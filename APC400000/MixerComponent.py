from itertools import ifilter
from _Framework.Control import RadioButtonControl, control_list
from _Framework.Dependency import depends
from _Framework.Util import nop
from _APC.MixerComponent import MixerComponent as MixerComponentBase

def _set_channel(controls, channel):
    for control in ifilter(None, controls or []):
        control.set_channel(channel)

    return


class MixerComponent(MixerComponentBase):

    @depends(show_message=nop)
    def __init__(self, num_tracks = 0, show_message = nop, *a, **k):
        self._button_index = 0
        super(MixerComponent, self).__init__(num_tracks=num_tracks, *a, **k)
        self._show_message = show_message
        self._pan_controls = None
        self._send_controls = None
        self._user_controls = None
        return

    def disconnect(self):
        super(MixerComponent, self).disconnect()
        self._pan_controls = None
        self._send_controls = None
        self._user_controls = None
        self._button_index = 0
        return

    def set_send_button_index(self, button_index):
        self._button_index = button_index
        if button_index < self.num_sends:
            self._set_send_index(button_index)
        else:
            self._set_send_index(None)
        return

    def on_send_index_changed(self):
        if self.is_enabled() and self._send_controls:
            self._show_controlled_sends_message()
        return

    def _show_controlled_sends_message(self):
        if self._send_index is not None:
            send_name = chr(ord('A') + self._send_index)
            self._show_message('Controlling Send %s' % send_name)
        return

    def set_pan_controls(self, controls):
        super(MixerComponent, self).set_pan_controls(controls)
        self._pan_controls = controls
        # self._update_pan_controls()
        if self.is_enabled() and controls:
            self._show_message('Controlling Pans')

    def set_send_controls(self, controls):
        super(MixerComponent, self).set_send_controls(controls)
        self._send_controls = controls
        # self._update_send_controls()
        if self.is_enabled() and controls:
            self._show_controlled_sends_message()

    def set_user_controls(self, controls):
        self._user_controls = controls
        # self._update_user_controls()
        if self.is_enabled() and controls:
            self._show_message('Controlling User Mappings')


    # def _update_pan_controls(self):
    #     _set_channel(self._pan_controls, 0)

    # def _update_send_controls(self):
    #     _set_channel(self._send_controls, 1 + self._button_index)

    # def _update_user_controls(self):
    #     _set_channel(self._user_controls, 4)

    # def update(self):
    #     super(MixerComponent, self).update()
    #     if self.is_enabled():
    #         self._update_pan_controls()
    #         self._update_send_controls()
    #         self._update_user_controls()
