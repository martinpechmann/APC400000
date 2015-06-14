from __future__ import with_statement
import Live
from itertools import chain, starmap, repeat
from _Framework.ClipCreator import ClipCreator
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.CompoundComponent import CompoundComponent
from _Framework.SubjectSlot import subject_slot, Subject, subject_slot_group
from _Framework.Util import forward_property, find_if
from _Framework.Layer import Layer

from Push.LoopSelectorComponent import LoopSelectorComponent
from Push.NoteEditorPaginator import NoteEditorPaginator
from Push.PlayheadComponent import PlayheadComponent
from Push.StepSeqComponent import DrumGroupFinderComponent, find_instrument_devices, find_drum_group_device

from APCDrumGroupComponent import APCDrumGroupComponent as DrumGroupComponent
from APCNoteEditorComponent import APCNoteEditorComponent as NoteEditorComponent
from APCMessenger import APCMessenger


class APCStepSeqComponent(CompoundComponent, APCMessenger):
    """ Step Sequencer Component """

    def __init__(self, clip_creator = ClipCreator(), skin = None, grid_resolution = None, note_editor_settings = None, *a, **k):
        super(APCStepSeqComponent, self).__init__(*a, **k)
        if not clip_creator:
            raise AssertionError
        if not skin:
            raise AssertionError
        self._grid_resolution = grid_resolution
        if note_editor_settings:
            self.register_component(note_editor_settings)
        self._note_editor, self._loop_selector, self._big_loop_selector, self._drum_group = self.register_components(NoteEditorComponent(settings_mode=note_editor_settings, clip_creator=clip_creator, grid_resolution=self._grid_resolution), LoopSelectorComponent(clip_creator=clip_creator), LoopSelectorComponent(clip_creator=clip_creator, measure_length=2.0), DrumGroupComponent())
        self._paginator = NoteEditorPaginator([self._note_editor])
        self._big_loop_selector.set_enabled(False)
        self._big_loop_selector.set_paginator(self._paginator)
        self._loop_selector.set_paginator(self._paginator)
        self._shift_button = None
        self._delete_button = None
        self._mute_button = None
        self._solo_button = None
        self._note_editor_matrix = None
        self._on_pressed_pads_changed.subject = self._drum_group
        self._on_detail_clip_changed.subject = self.song().view
        self._detail_clip = None
        self._playhead = None
        self._playhead_component = self.register_component(PlayheadComponent(grid_resolution=grid_resolution, paginator=self._paginator, follower=self._loop_selector, notes=chain(*starmap(repeat, ((54, 4),
         (55, 4),
         (56, 4),
         (57, 4)))), triplet_notes=chain(*starmap(repeat, ((54, 3),
         (55, 3),
         (56, 3),
         (57, 3)))), channels=repeat(range(4,8),4), triplet_channels=repeat(range(4,7),4)))
        self._skin = skin
        self._playhead_color = 'NoteEditor.Playhead'
        self._setup_drum_group_finder()
        return

    def _setup_drum_group_finder(self):
        self._drum_group_finder = DrumGroupFinderComponent()
        self._on_drum_group_changed.subject = self._drum_group_finder
        self._drum_group_finder.update()

    @subject_slot('drum_group')
    def _on_drum_group_changed(self):
        self.set_drum_group_device(self._drum_group_finder.drum_group)

    def on_selected_track_changed(self):
        self.set_drum_group_device(self._drum_group_finder.drum_group)

    def set_velocity_slider(self, button_slider):
        self._note_editor.set_velocity_slider(button_slider)

    def set_playhead(self, playhead):
        self._playhead = playhead
        self._playhead_component.set_playhead(playhead)
        self._update_playhead_color()

    def _get_playhead_color(self):
        return self._playhead_color

    def _set_playhead_color(self, value):
        self._playhead_color = 'NoteEditor.' + value
        self._update_playhead_color()

    playhead_color = property(_get_playhead_color, _set_playhead_color)

    def _is_triplet_quantization(self):
        return self._grid_resolution.clip_grid[1]

    def _update_playhead_color(self):
        if self.is_enabled() and self._skin and self._playhead:
            self._playhead.velocity = int(self._skin[self._playhead_color])

    def set_drum_group_device(self, drum_group_device):
        if (drum_group_device and not drum_group_device.can_have_drum_pads):
            raise AssertionError
        self._drum_group.set_drum_group_device(drum_group_device)
        self._on_selected_drum_pad_changed.subject = drum_group_device.view if drum_group_device else None
        self._on_selected_drum_pad_changed()
        return

    def set_touch_strip(self, touch_strip):
        self._drum_group.set_page_strip(touch_strip)

    def set_detail_touch_strip(self, touch_strip):
        self._drum_group.set_scroll_strip(touch_strip)

    def set_quantize_button(self, button):
        self._drum_group.set_quantize_button(button)

    def set_full_velocity_button(self, button):
        self._note_editor.set_full_velocity_button(button)

    def set_select_button(self, button):
        self._drum_group.set_select_button(button)
        self._loop_selector.set_select_button(button)

    def set_mute_button(self, button):
        self._drum_group.set_mute_button(button)
        self._note_editor.set_mute_button(button)
        self._mute_button = button

    def set_solo_button(self, button):
        self._drum_group.set_solo_button(button)
        self._solo_button = button

    def set_shift_button(self, button):
        self._big_loop_selector.set_select_button(button)
        self._shift_button = button
        self._on_shift_value.subject = button

    def set_delete_button(self, button):
        self._delete_button = button
        self._drum_group.set_delete_button(button)

    def set_next_loop_page_button(self, button):
        self._loop_selector.next_page_button.set_control_element(button)

    def set_prev_loop_page_button(self, button):
        self._loop_selector.prev_page_button.set_control_element(button)

    def set_loop_selector_matrix(self, matrix):
        self._loop_selector.set_loop_selector_matrix(matrix)

    def set_short_loop_selector_matrix(self, matrix):
        self._loop_selector.set_short_loop_selector_matrix(matrix)

    def set_follow_button(self, button):
        self._loop_selector.set_follow_button(button)
        self._big_loop_selector.set_follow_button(button)

    def set_drum_matrix(self, matrix):
        self._drum_group.set_drum_matrix(matrix)

    def set_drum_bank_up_button(self, button):
        self._drum_group.set_scroll_page_up_button(button)

    def set_drum_bank_down_button(self, button):
        self._drum_group.set_scroll_page_down_button(button)

    def set_drum_bank_detail_up_button(self, button):
        self._drum_group.set_scroll_up_button(button)

    def set_drum_bank_detail_down_button(self, button):
        self._drum_group.set_scroll_down_button(button)

    def set_button_matrix(self, matrix):
        self._note_editor_matrix = matrix
        self._update_note_editor_matrix()

    def set_quantization_buttons(self, buttons):
        self._grid_resolution.set_buttons(buttons)

    def set_velocity_control(self, control):
        self._note_editor.set_velocity_control(control)

    def set_length_control(self, control):
        self._note_editor.set_length_control(control)

    def set_nudge_control(self, control):
        self._note_editor.set_nudge_control(control)

    @forward_property('_note_editor')
    def full_velocity(self):
        pass

    def update(self):
        super(APCStepSeqComponent, self).update()
        self._on_detail_clip_changed()
        self._update_playhead_color()

    @subject_slot('detail_clip')
    def _on_detail_clip_changed(self):
        clip = self.song().view.detail_clip
        clip = clip if self.is_enabled() and clip and clip.is_midi_clip else None
        self._detail_clip = clip
        self._note_editor.set_detail_clip(clip)
        self._loop_selector.set_detail_clip(clip)
        self._big_loop_selector.set_detail_clip(clip)
        self._playhead_component.set_clip(self._detail_clip)
        return

    @subject_slot('value')
    def _on_shift_value(self, value):
        if self.is_enabled():
            self._update_note_editor_matrix(enable_big_loop_selector=value and not self._loop_selector.is_following)

    @subject_slot('selected_drum_pad')
    def _on_selected_drum_pad_changed(self):
        drum_group_view = self._on_selected_drum_pad_changed.subject
        if drum_group_view:
            selected_drum_pad = drum_group_view.selected_drum_pad
            if selected_drum_pad:
                self._note_editor.editing_note = selected_drum_pad.note

    @subject_slot('pressed_pads')
    def _on_pressed_pads_changed(self):
        self._note_editor.modify_all_notes_enabled = bool(self._drum_group.pressed_pads)

    def _update_note_editor_matrix(self, enable_big_loop_selector = False):
        if enable_big_loop_selector:
            self._note_editor.set_enabled(False)
            self._note_editor.set_button_matrix(None)
            self._big_loop_selector.set_enabled(True)
            self._big_loop_selector.set_loop_selector_matrix(self._note_editor_matrix)
        else:
            self._big_loop_selector.set_enabled(False)
            self._big_loop_selector.set_loop_selector_matrix(None)
            self._note_editor.set_enabled(True)
            self._note_editor.set_button_matrix(self._note_editor_matrix)
        return
