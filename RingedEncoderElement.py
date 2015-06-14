from _APC.RingedEncoderElement import RingedEncoderElement, RING_SIN_VALUE
from _Framework.EncoderElement import TouchEncoderElementBase
from APCMessenger import APCMessenger

class RingedEncoderElement(RingedEncoderElement, TouchEncoderElementBase, APCMessenger):
  """ Modified to provide pseudo-relative encoder behaviour """
  def __init__(self, *a, **k):
    self._prev_value = 0
    super(RingedEncoderElement, self).__init__(*a, **k)

  def disconnect(self):
    self.send_value(0, force=True)
    super(RingedEncoderElement, self).disconnect()

  def is_pressed(self):
    """ We're only pretending to be a touch encoder to keep Push happy"""
    return False

  def _update_ring_mode(self):
    """ Modified for pseudo-relative behaviour """
    if self.normalized_value_listener_count():
      self._ring_mode_button.send_value(RING_SIN_VALUE, force=True)
      self._prev_value = 64
      self.send_value(64, force=True)
    else:
      super(RingedEncoderElement, self)._update_ring_mode()

  def normalize_value(self, value):
    """ This is not actually a relative value, but we'll fake it """
    delta = (value - self._prev_value) * 0.01
    if value == 127:
      delta = 0.01
    elif value == 0:
      delta = -0.01
    self._prev_value = value
    return delta