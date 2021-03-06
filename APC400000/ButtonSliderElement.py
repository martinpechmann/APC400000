from _Framework.ButtonSliderElement import ButtonSliderElement as ButtonSliderElementBase
from SkinDefault import BiLedColors

class ButtonSliderElement(ButtonSliderElementBase):
  """ Fixes the broken scaling code on the _Framework example
  caused by odd numbers of buttons 
  
  Also adds force_send
  """

  def disconnect(self):
    super(ButtonSliderElementBase, self).disconnect()
    for button in self._buttons:
      button.turn_off()
    self._buttons = None
    return

  def send_value(self, value, force_send = False):
    if force_send or value != self._last_sent_value:
      num_buttons = len(self._buttons)
      index_to_light = 0
      if value > 0:
        index_to_light = int(round((num_buttons - 1) * float(value) / 127)) 
        for index in xrange(num_buttons):
          if index <= index_to_light:
            self._buttons[index].set_light(self._button_color(index))
          else:
            self._buttons[index].turn_off()
      else:
        for index in xrange(num_buttons):
          self._buttons[index].turn_off()

      self._last_sent_value = value

  def _button_color(self, index):
    return "NoteEditor.Step." + [
      "Low",
      "Low",
      "Medium",
      "High",
      "Full"
    ][index]
