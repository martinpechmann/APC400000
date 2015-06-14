from itertools import imap, ifilter
from _Framework.Util import find_if, first
from _Framework.SubjectSlot import subject_slot
from _Framework.DrumGroupComponent import DrumGroupComponent
from MatrixMaps import PAD_FEEDBACK_CHANNELS
from APCMessenger import APCMessenger

class APCDrumGroupComponent(DrumGroupComponent, APCMessenger):
  """ Customized to use its own feedback channel """

  def set_drum_matrix(self, matrix):
    self.drum_matrix.set_control_element(matrix)
    for button in self.drum_matrix:
      button.channel = PAD_FEEDBACK_CHANNELS[button.coordinate[1]]

    if self._selected_pads:
      self._selected_pads = []
      self.notify_pressed_pads()
    self._create_and_set_pad_translations()
    self._update_control_from_script()
    self._update_identifier_translations()
    self._update_led_feedback()

  def _create_and_set_pad_translations(self):

    def create_translation_entry(button):
      row, col = button.coordinate
      button.identifier = row + 54
      return (col,
       row,
       button.identifier,
       button.channel)

    if self._can_set_pad_translations():
      translations = tuple(map(create_translation_entry, self.drum_matrix))
      self._set_pad_translated_identifiers()
    else:
      translations = None
      self._set_non_pad_translated_identifiers()
    self._set_pad_translations(translations)
    return

  # def _update_control_from_script(self):
  #   """ Patched to use our own feedback channel """
  #   takeover_drums = self._takeover_drums or self._selected_pads
  #   profile = 'default' if takeover_drums else 'drums'
  #   if self._drum_matrix:
  #     for button, (col, _) in ifilter(first, self._drum_matrix.iterbuttons()):
  #       button.set_channel(PAD_FEEDBACK_CHANNELS[col])
  #       button.set_enabled(takeover_drums)
  #       button.sensitivity_profile = profile

  def on_selected_track_changed(self):
    if self.song().view.selected_track.has_midi_input:
      self.set_enabled(True)
      self.update()
    else:
      self.set_enabled(False)
      self._update_led_feedback()

  def _update_led_feedback(self):
    if (not self.is_enabled()) and self.drum_matrix:
      for button in self.drum_matrix:
        button.color = 'DrumGroup.PadInvisible'
    else:
      super(APCDrumGroupComponent, self)._update_led_feedback()

  # def _update_drum_pad_leds(self):
  #   if (not self.is_enabled()) and self._drum_matrix:
  #     for button, (col, row) in ifilter(first, self._drum_matrix.iterbuttons()):
  #       button.set_light('DrumGroup.PadInvisible')
  #   else:
  #     super(APCDrumGroupComponent, self)._update_drum_pad_leds()

  def set_select_button(self, button):
    self.select_button.set_control_element(button)

  def set_mute_button(self, button):
    self.mute_button.set_control_element(button)

  def set_solo_button(self, button):
    self.solo_button.set_control_element(button)

  def set_quantize_button(self, button):
    self.quantize_button.set_control_element(button)

  def set_delete_button(self, button):
    self.delete_button.set_control_element(button)

  def set_drum_group_device(self, drum_group_device):
    super(APCDrumGroupComponent, self).set_drum_group_device(drum_group_device)
    self._on_chains_changed.subject = self._drum_group_device
    self.notify_contents()

  @subject_slot('chains')
  def _on_chains_changed(self):
    self._update_led_feedback()
    self.notify_contents()

  def delete_pitch(self, drum_pad):
    clip = self.song().view.detail_clip
    if clip:
      loop_length = clip.loop_end - clip.loop_start
      clip.remove_notes(clip.loop_start, drum_pad.note, loop_length, 1)
      self.show_message('Notes deleted:  %s' % drum_pad.name)

  def select_drum_pad(self, drum_pad):
    pass
