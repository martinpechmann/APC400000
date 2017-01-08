from __future__ import with_statement
import sys
from functools import partial
from contextlib import contextmanager

import Live
from _Framework.BackgroundComponent import BackgroundComponent, ModifierBackgroundComponent
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ClipCreator import ClipCreator
from _Framework.ComboElement import ComboElement, DoublePressElement, MultiElement, DoublePressContext
from _Framework.ControlSurface import OptimizedControlSurface
from _Framework.Dependency import inject
from _Framework.Layer import Layer
from _Framework.M4LInterfaceComponent import M4LInterfaceComponent
from _Framework.ModesComponent import LazyComponentMode, AddLayerMode, CompoundMode, LatchingBehaviour
from _Framework.Resource import PrioritizedResource, DEFAULT_PRIORITY
from _Framework.SessionRecordingComponent import SessionRecordingComponent
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.Skin import merge_skins
from _Framework.Util import const, recursive_map
# from _Framework.EncoderElement import FineGrainWithModifierEncoderElement

from Actions import DuplicateLoopComponent, UndoRedoComponent
from AutoArmComponent import AutoArmComponent
from GridResolution import GridResolution

# from _APC.APC import APC
from _APC.DeviceBankButtonElement import DeviceBankButtonElement
from _APC.DeviceComponent import DeviceComponent
from _APC.DetailViewCntrlComponent import DetailViewCntrlComponent
from _APC.SessionComponent import SessionComponent
# from SessionComponent import SessionComponent

from APC import APC
from AltDeviceComponent import AltDeviceComponent
from ButtonSliderElement import ButtonSliderElement
from ControlElementUtils import make_configurable_button, make_button, make_encoder, make_slider, make_ring_encoder, make_pedal_button
from LatchingToggleModesComponent import LatchingToggleModesComponent
# from MatrixMaps import PAD_TRANSLATIONS, FEEDBACK_CHANNELS
from MixerComponent import MixerComponent
from ProviderDeviceComponent import ProviderDeviceComponent
from QuantizationComponent import QuantizationComponent
from SkinDefault import make_rgb_skin, make_biled_skin, make_default_skin, make_stop_button_skin
from TransportComponent import TransportComponent

from APCNoteSettingsComponent import NoteEditorSettingsComponent
from APCStepSeqComponent import APCStepSeqComponent as StepSeqComponent

from PlayheadElement import PlayheadElement

# Monkeypatch things
# import ControlElementUtils
# import SkinDefault
# sys.modules['_APC.ControlElementUtils'] = ControlElementUtils
# sys.modules['_APC.SkinDefault'] = SkinDefault

NUM_TRACKS = 8
NUM_SCENES = 5

class APC400000(APC, OptimizedControlSurface):

    def __init__(self, *a, **k):
        super(APC400000, self).__init__(*a, **k)
        self._double_press_context = DoublePressContext()
        self._default_skin = make_default_skin()
        self._color_skin = merge_skins(self._default_skin, make_biled_skin())
        self._stop_button_skin = merge_skins(self._default_skin, make_stop_button_skin())
        with self.component_guard():
            self._note_editor_settings = []
            self._create_controls()
            self._init_background()
            self._create_undo_redo_actions()
            self._create_session()
            self._create_mixer()
            self._create_transport()
            self._create_device()
            self._create_view_control()
            self._create_quantization_selection()
            self._create_recording()
            self._create_duplicate_loop()
            self._init_auto_arm()
            self._create_sequencer()
            self._create_track_modes()
            self._create_encoder_modes_session()
            self._create_main_modes()
            self._create_m4l_interface()
            self._session.set_mixer(self._mixer)
            #self.set_pad_translations(PAD_TRANSLATIONS)
            #self.set_feedback_channels(FEEDBACK_CHANNELS)

        self.set_highlighting_session_component(self._session)
        self.set_device_component(self._device)
        self._device_selection_follows_track_selection = True

    @contextmanager
    def component_guard(self):
        """ Customized to inject additional things """
        with super(APC400000, self).component_guard():
            with self.make_injector().everywhere():
                yield

    def make_injector(self):
        """ Adds some additional stuff to the injector, used in APCMessenger """
        return inject(
            double_press_context = const(self._double_press_context),
            control_surface = const(self),
            log_message = const(self.log_message))

    def _with_shift(self, button):
        return ComboElement(button, modifiers=[self._shift_button])

    def _create_controls(self):

        make_on_off_button = partial(make_configurable_button, skin=self._default_skin)
        make_color_button = partial(make_configurable_button, skin=self._color_skin)
        make_stop_button = partial(make_configurable_button, skin=self._stop_button_skin)

        self._shift_button = make_button(0, 98, name='Shift_Button', resource_type=PrioritizedResource)
        self._left_button = make_button(0, 97, name='Bank_Select_Left_Button')
        self._right_button = make_button(0, 96, name='Bank_Select_Right_Button')
        self._up_button = make_button(0, 94, name='Bank_Select_Up_Button')
        self._down_button = make_button(0, 95, name='Bank_Select_Down_Button')
        self._stop_buttons = ButtonMatrixElement(rows=[[ make_stop_button(track, 52, name='%d_Stop_Button' % track) for track in xrange(NUM_TRACKS) ]], name="Stop_Buttons")
        self._stop_all_button = make_button(0, 81, name='Stop_All_Clips_Button')
        self._scene_launch_buttons_raw = [ make_color_button(0, scene + 82, name='Scene_%d_Launch_Button' % scene) for scene in xrange(NUM_SCENES) ]
        self._scene_launch_buttons = ButtonMatrixElement(rows=[self._scene_launch_buttons_raw], name="Scene_Launch_Buttons")
        self._matrix_rows_raw = [ [ make_color_button(track, 53 + scene, name='%d_Clip_%d_Button' % (track, scene)) for track in xrange(NUM_TRACKS) ] for scene in xrange(NUM_SCENES) ]
        self._session_matrix = ButtonMatrixElement(rows=self._matrix_rows_raw, name='Button_Matrix')
        self._pan_button = make_on_off_button(0, 87, name='Pan_Button')
        self._send_a_button = make_on_off_button(0, 88, name='Send_A_Button')
        self._send_b_button = make_on_off_button(0, 89, name='Send_B_Button')
        self._send_c_button = make_on_off_button(0, 90, name='Send_C_Button')
        self._mixer_encoders = ButtonMatrixElement(rows=[[ make_ring_encoder(48 + track, 56 + track, name='Track_Control_%d' % track) for track in xrange(NUM_TRACKS) ]], name="Track_Controls")
        # self._mixer_encoders_raw = [ make_ring_encoder(48 + track, 56 + track, name='Track_Control_%d' % track) for track in xrange(NUM_TRACKS) ]
        # self._mixer_encoders = ButtonMatrixElement(rows=[[FineGrainWithModifierEncoderElement(encoder, self._shift_button) for encoder in self._mixer_encoders_raw]], name="Track_Controls")
        self._volume_controls = ButtonMatrixElement(rows=[[ make_slider(track, 7, name='%d_Volume_Control' % track) for track in xrange(NUM_TRACKS) ]])
        self._master_volume_control = make_slider(0, 14, name='Master_Volume_Control')
        self._prehear_control = make_encoder(0, 47, name='Prehear_Volume_Control')
        self._crossfader_control = make_slider(0, 15, name='Crossfader')
        self._raw_select_buttons = [ make_on_off_button(channel, 51, name='%d_Select_Button' % channel) for channel in xrange(NUM_TRACKS) ]
        self._arm_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 48, name='%d_Arm_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Arm_Buttons")
        self._solo_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 49, name='%d_Solo_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Solo_Buttons")
        self._mute_buttons = ButtonMatrixElement(rows=[[ make_on_off_button(channel, 50, name='%d_Mute_Button' % channel) for channel in xrange(NUM_TRACKS) ]], name="Mute_Buttons")
        self._select_buttons = ButtonMatrixElement(rows=[self._raw_select_buttons], name="Select_Buttons")
        self._master_select_button = make_on_off_button(channel=0, identifier=80, name='Master_Select_Button')
        # self._send_select_buttons = ButtonMatrixElement(rows=[[ ComboElement(button, modifiers=[self._sends_button]) for button in self._raw_select_buttons ]])
        self._quantization_buttons = ButtonMatrixElement(rows=[[ ComboElement(button, modifiers=[self._shift_button]) for button in self._raw_select_buttons ]], name="Quantization_Buttons")
        self._play_button = make_on_off_button(0, 91, name='Play_Button')
        self._stop_button = make_on_off_button(0, 92, name='Stop_Button')
        self._record_button = make_on_off_button(0, 93, name='Record_Button')
        self._nudge_down_button = make_button(0, 101, name='Nudge_Down_Button')
        self._nudge_up_button = make_button(0, 100, name='Nudge_Up_Button')
        self._tap_tempo_button = make_button(0, 99, name='Tap_Tempo_Button')
        self._device_controls = ButtonMatrixElement(rows=[[ make_ring_encoder(16 + index, 24 + index, name='Device_Control_%d' % index) for index in xrange(8) ]], name="Device_Controls")
        self._device_control_buttons_raw = [ make_on_off_button(0, 58 + index) for index in xrange(8) ]
        self._device_bank_buttons = ButtonMatrixElement(rows=[[ DeviceBankButtonElement(button, modifiers=[self._shift_button]) for button in self._device_control_buttons_raw ]], name="Device_Bank_Buttons")
        self._device_lock_button = self._device_control_buttons_raw[0]
        self._device_lock_button.name = 'Device_Lock_Button'
        self._device_on_off_button = self._device_control_buttons_raw[1]
        self._device_on_off_button.name = 'Device_On_Off_Button'
        self._device_prev_bank_button = self._device_control_buttons_raw[2]
        self._device_prev_bank_button.name = 'Device_Prev_Bank_Button'
        self._device_next_bank_button = self._device_control_buttons_raw[3]
        self._device_next_bank_button.name = 'Device_Next_Bank_Button'
        self._clip_device_button = self._device_control_buttons_raw[4]
        self._clip_device_button.name = 'Clip_Device_Button'
        self._automation_button = self._device_control_buttons_raw[5]
        self._automation_button.name = 'Automation_Arm_Button'
        self._prev_device_button = self._device_control_buttons_raw[6]
        self._prev_device_button.name = 'Prev_Device_Button'
        self._next_device_button = self._device_control_buttons_raw[7]
        self._next_device_button.name = 'Next_Device_Button'
        self._foot_pedal_1_button = DoublePressElement(make_pedal_button(64, name='Foot_Pedal_1'))
        self._foot_pedal_2_button = DoublePressElement(make_pedal_button(67, name='Foot_Pedal_2'))
        self._shifted_matrix = ButtonMatrixElement(rows=recursive_map(self._with_shift, self._matrix_rows_raw), name="Shifted_Matrix")
        self._shifted_scene_buttons = ButtonMatrixElement(rows=[[ self._with_shift(button) for button in self._scene_launch_buttons_raw ]], name="Shifted_Scene_Buttons")
        self._double_press_rows = recursive_map(DoublePressElement, self._matrix_rows_raw)
        self._double_press_matrix = ButtonMatrixElement(name='Double_Press_Matrix', rows=self._double_press_rows)
        self._double_press_event_matrix = ButtonMatrixElement(name='Double_Press_Event_Matrix', rows=recursive_map(lambda x: x.double_press, self._double_press_rows))
        self._velocity_slider = ButtonSliderElement(tuple(self._scene_launch_buttons_raw[::-1]))
        self._grid_resolution = GridResolution()
        self._playhead_element = PlayheadElement(self._c_instance.playhead)
        # self._playhead_element.name = 'Playhead_Element'
        # self._playhead_element.proxied_object = self._c_instance.playhead

    def _init_background(self):
        self._background = BackgroundComponent(is_root=True)
        self._background.layer = Layer(
            button_matrix = self._session_matrix,
            select_buttons = self._select_buttons,
            priority = DEFAULT_PRIORITY-3)
        self._mod_background = ModifierBackgroundComponent(is_root=True)
        self._mod_background.layer = Layer(shift_button=self._shift_button)

    def _create_undo_redo_actions(self):
        self._undo_redo = UndoRedoComponent(name='Undo_Redo', is_root=True)
        self._undo_redo.layer = Layer(undo_button=self._with_shift(self._nudge_down_button), redo_button=self._with_shift(self._nudge_up_button))

    def _create_duplicate_loop(self):
        self._duplicate_loop = DuplicateLoopComponent(name='Duplicate_Loop', layer=Layer(action_button=self._send_a_button), is_enabled=False)

    def _create_session(self):
        self._session = SessionComponent(NUM_TRACKS, NUM_SCENES, auto_name=True, is_enabled=False, enable_skinning=True)
        self._session_zoom = SessionZoomingComponent(self._session, name='Session_Overview', is_enabled=False, enable_skinning=True)

    def _session_layer(self):
        return Layer(track_bank_left_button=self._left_button, track_bank_right_button=self._right_button, scene_bank_up_button=self._up_button, scene_bank_down_button=self._down_button, stop_track_clip_buttons=self._stop_buttons, stop_all_clips_button=self._stop_all_button, scene_launch_buttons=self._scene_launch_buttons, clip_launch_buttons=self._session_matrix)

    def _session_zoom_layer(self):
        return Layer(button_matrix=self._shifted_matrix, nav_left_button=self._with_shift(self._left_button), nav_right_button=self._with_shift(self._right_button), nav_up_button=self._with_shift(self._up_button), nav_down_button=self._with_shift(self._down_button), scene_bank_buttons=self._shifted_scene_buttons)

    def _create_track_modes(self):
        self._track_modes = LatchingToggleModesComponent(name='Track_Modes')
        self._track_modes.add_mode('pan', [AddLayerMode(self._mixer, Layer(pan_controls=self._mixer_encoders))])
        self._track_modes.add_mode('send_a', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 0)])
        self._track_modes.add_mode('send_b', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 1)])
        self._track_modes.add_mode('send_c', [AddLayerMode(self._mixer, Layer(send_controls=self._mixer_encoders)), partial(self._mixer.set_send_button_index, 2)])
        self._track_modes.layer = Layer(pan_button=self._pan_button, send_a_button=self._send_a_button, send_b_button=self._send_b_button, send_c_button=self._send_c_button)
        self._track_modes.selected_mode = 'pan'

    def _create_encoder_modes_session(self):
        self._encoder_modes_session = LatchingToggleModesComponent(name='Encoder_Modes_(Session)')
        self._encoder_modes_session.add_mode('mixer', self._track_modes)
        self._encoder_modes_session.add_mode('device', [AddLayerMode(self._alt_device, Layer(parameter_controls=self._mixer_encoders, lock_button=self._pan_button, on_off_button=self._send_a_button, bank_prev_button=self._send_b_button, bank_next_button=self._send_c_button))])
        #self._encoder_modes.add_mode('user', [AddLayerMode(self._mixer, Layer(user_controls=self._mixer_encoders))])
        #self._encoder_modes.layer = Layer(mixer_button=self._with_shift(self._pan_button), device_button=self._with_shift(self._send_a_button), user_button=self._with_shift(self._send_c_button))
        self._encoder_modes_session.layer = Layer(shift_button=self._shift_button)
        self._encoder_modes_session.selected_mode = 'mixer'

    def _create_encoder_modes_sequencer(self):
        self._encoder_modes_sequencer = LatchingToggleModesComponent(name='Encoder_Modes_(Sequencer)', is_enabled=False)
        self._encoder_modes_sequencer.add_mode('note_settings', [AddLayerMode(self._note_editor_settings._mode_selector, Layer(toggle_button=self._pan_button)), AddLayerMode(self._sequencer, Layer(mute_button=self._send_b_button, delete_button=self._send_c_button)), self._duplicate_loop])
        self._encoder_modes_sequencer.add_mode('device', [AddLayerMode(self._alt_device, Layer(parameter_controls=self._mixer_encoders, lock_button=self._pan_button, on_off_button=self._send_a_button, bank_prev_button=self._send_b_button, bank_next_button=self._send_c_button))])
        self._encoder_modes_sequencer.add_mode('mixer', self._track_modes)
        self._encoder_modes_sequencer.layer = Layer(toggle_button=self._nudge_up_button, shift_button=self._shift_button)
        self._encoder_modes_sequencer.selected_mode = 'note_settings'
        return self._encoder_modes_sequencer

    def _create_main_modes(self):

        def configure_note_editor_settings(parameter_provider):
            self._note_editor_settings.parameter_provider = parameter_provider

        def takeover_pads(takeover):
            return partial(self._sequencer._drum_group._set_control_pads_from_script, takeover)

        self._main_modes = LatchingToggleModesComponent(name='Session_Modes', is_enabled=False)
        self._main_modes.add_mode('session', [AddLayerMode(self._session, self._session_layer()), AddLayerMode(self._session_zoom, self._session_zoom_layer()), self._encoder_modes_session, AddLayerMode(self._encoder_modes_session, Layer(toggle_button=self._nudge_up_button))])
        self._main_modes.add_mode('sequencer', [AddLayerMode(self._sequencer, self._sequencer_layer()), LazyComponentMode(self._create_encoder_modes_sequencer), configure_note_editor_settings(self._device), (takeover_pads(False), takeover_pads(True)), self._restore_auto_arm])
        self._main_modes.layer = Layer(toggle_button=self._nudge_down_button, shift_button=self._shift_button)
        self._main_modes.selected_mode = 'session'

    def _create_mixer(self):
        self._mixer = MixerComponent(NUM_TRACKS, auto_name=True, is_enabled=False, invert_mute_feedback=True, layer=Layer(volume_controls=self._volume_controls, arm_buttons=self._arm_buttons, solo_buttons=self._solo_buttons, mute_buttons=self._mute_buttons, shift_button=self._shift_button, track_select_buttons=self._select_buttons, prehear_volume_control=self._prehear_control, crossfader_control=self._crossfader_control))
        self._mixer.master_strip().layer = Layer(volume_control=self._master_volume_control, select_button=self._master_select_button)

    def _create_transport(self):
        self._transport = TransportComponent(name='Transport', is_enabled=False, layer=Layer(shift_button=self._shift_button, play_button=self._play_button, stop_button=self._stop_button, record_button=self._with_shift(self._record_button), metronome_button=self._with_shift(self._tap_tempo_button), tap_tempo_button=self._tap_tempo_button), play_toggle_model_transform=lambda v: v)

    def _create_device(self):
        #self._device = DeviceComponent(name='Device', is_enabled=False, layer=Layer(parameter_controls=self._device_controls, bank_buttons=self._device_bank_buttons, bank_prev_button=self._device_prev_bank_button, bank_next_button=self._device_next_bank_button, on_off_button=self._device_on_off_button, lock_button=self._device_lock_button))
        self._device = ProviderDeviceComponent(name='Device', is_enabled=False, device_selection_follows_track_selection=True, layer=Layer(parameter_controls=self._device_controls, bank_buttons=self._device_bank_buttons, bank_prev_button=self._device_prev_bank_button, bank_next_button=self._device_next_bank_button, on_off_button=self._device_on_off_button, lock_button=self._device_lock_button))
        self._alt_device = AltDeviceComponent(self, name='Alt_Device', is_enabled=False)

    def _create_view_control(self):
        self._view_control = DetailViewCntrlComponent(name='View_Control', is_enabled=False, layer=Layer(device_nav_left_button=self._prev_device_button, device_nav_right_button=self._next_device_button, device_clip_toggle_button=self._clip_device_button))
        self._view_control.device_clip_toggle_button.pressed_color = 'DefaultButton.On'

    def _create_quantization_selection(self):
        self._quantization_selection = QuantizationComponent(name='Quantization_Selection', is_enabled=False, layer=Layer(quantization_buttons=self._quantization_buttons))

    def _create_recording(self):
        record_button = MultiElement(self._record_button, self._foot_pedal_1_button.single_press)
        self._session_recording = SessionRecordingComponent(ClipCreator(), self._view_control, name='Session_Recording', is_enabled=False, layer=Layer(new_button=self._foot_pedal_1_button.double_press, record_button=record_button, automation_button=self._automation_button, _uses_foot_pedal=self._foot_pedal_1_button))

    def _create_m4l_interface(self):
        self._m4l_interface = M4LInterfaceComponent(controls=self.controls, component_guard=self.component_guard, priority=DEFAULT_PRIORITY+1)
        self.get_control_names = self._m4l_interface.get_control_names
        self.get_control = self._m4l_interface.get_control
        self.grab_control = self._m4l_interface.grab_control
        self.release_control = self._m4l_interface.release_control

    def get_matrix_button(self, column, row):
        return self._matrix_rows_raw[row][column]

    def _product_model_id_byte(self):
        return 115
    
    def _add_note_editor_setting(self):
        self._note_editor_settings = NoteEditorSettingsComponent(
            self._grid_resolution,
            initial_encoder_layer = Layer(initial_notes_encoders=self._mixer_encoders),
            encoder_layer = Layer(notes_encoders=self._mixer_encoders),
            automation_encoder_layer = Layer(parameter_encoders=self._device_controls))
        return self._note_editor_settings

    def _create_sequencer(self):
        self._sequencer = StepSeqComponent(name='Step Sequencer', skin=self._color_skin, grid_resolution=self._grid_resolution, note_editor_settings=self._add_note_editor_setting())

    def _sequencer_layer(self):
        return Layer(
            velocity_slider = ButtonSliderElement(tuple(self._scene_launch_buttons_raw[::-1])),
            drum_matrix = self._session_matrix.submatrix[:4, 1:5],
            button_matrix = self._double_press_matrix.submatrix[4:8, 1:5],
            select_button = self._stop_all_button,
            # mute_button = self._send_b_button,
            # delete_button = self._send_c_button,
            playhead = self._playhead_element,
            quantization_buttons = self._stop_buttons,
            shift_button = self._shift_button,
            loop_selector_matrix = self._double_press_matrix.submatrix[:8, :1],
            short_loop_selector_matrix = self._double_press_event_matrix.submatrix[:8, :1],
            prev_loop_page_button = self._left_button,
            next_loop_page_button = self._right_button,
            drum_bank_detail_up_button = self._with_shift(self._up_button),
            drum_bank_detail_down_button = self._with_shift(self._down_button),
            drum_bank_up_button = self._up_button,
            drum_bank_down_button = self._down_button)


    # Make these prioritized resources, which share between Layers() equally
    # Rather than building a stack
    # self._pan_button._resource_type = PrioritizedResource 
    # self._user_button._resource_type = PrioritizedResource 

    # def _create_session_mode(self): 
    #   """ Switch between Session and StepSequencer modes """
    #   self._session_mode = ModesComponent(name='Session_Mode', is_enabled = False)
    #   self._session_mode.default_behaviour = ImmediateBehaviour()
    #   self._session_mode.add_mode('session', self._session_mode_layers())
    #   self._session_mode.add_mode('session_2', self._session_mode_layers())
    #   self._session_mode.add_mode('sequencer', (self._sequencer, self._sequencer_layer()))
    #   self._session_mode.layer = Layer(
    #       session_button = self._pan_button,
    #       session_2_button = self._sends_button, 
    #       sequencer_button = self._user_button)
    #   self._session_mode.selected_mode = "session"
  
    # def _session_mode_layers(self):
    #   return [ self._session, self._session_zoom]
  
    # def _session_layer(self):
    #   def when_bank_on(button):
    #     return self._bank_toggle.create_toggle_element(on_control=button)
    #   def when_bank_off(button):
    #     return self._bank_toggle.create_toggle_element(off_control=button)
    #   return Layer(
    #     track_bank_left_button = when_bank_off(self._left_button), 
    #     track_bank_right_button = when_bank_off(self._right_button), 
    #     scene_bank_up_button = when_bank_off(self._up_button), 
    #     scene_bank_down_button = when_bank_off(self._down_button), 
    #     page_left_button = when_bank_on(self._left_button), 
    #     page_right_button = when_bank_on(self._right_button), 
    #     page_up_button = when_bank_on(self._up_button), 
    #     page_down_button = when_bank_on(self._down_button), 
    #     stop_track_clip_buttons = self._stop_buttons,
    #     stop_all_clips_button = self._stop_all_button, 
    #     scene_launch_buttons = self._scene_launch_buttons, 
    #     clip_launch_buttons = self._session_matrix)
  
    # def _session_zoom_layer(self):
    #   return Layer(button_matrix=self._shifted_matrix, 
    #     nav_left_button=self._with_shift(self._left_button), 
    #     nav_right_button=self._with_shift(self._right_button), 
    #     nav_up_button=self._with_shift(self._up_button), 
    #     nav_down_button=self._with_shift(self._down_button), 
    #     scene_bank_buttons=self._shifted_scene_buttons)

    def _init_auto_arm(self):
        self._auto_arm = AutoArmComponent(name='Auto_Arm', is_enabled = True)

    # # EVENT HANDLING FUNCTIONS
    # def reset_controlled_track(self):
    #     self.set_controlled_track(self.song().view.selected_track)
  
    # def update(self):
    #     self.reset_controlled_track()
    #     super(APC400000, self).update()

    # def _on_selected_track_changed(self):
    #     self.reset_controlled_track()
    #     if self._auto_arm.needs_restore_auto_arm:
    #         self.schedule_message(1, self._auto_arm.restore_auto_arm)
    #     super(APC400000, self)._on_selected_track_changed()

    def _restore_auto_arm(self):
        if self._auto_arm.needs_restore_auto_arm:
            self.schedule_message(1, self._auto_arm.restore_auto_arm)
