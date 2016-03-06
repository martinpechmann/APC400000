import Live
from _Framework.SubjectSlot import subject_slot
from _APC.DeviceComponent import DeviceComponent

class AltDeviceComponent(DeviceComponent):

    def __init__(self, control_surface = None, *a, **k):
        super(AltDeviceComponent, self).__init__(*a, **k)
        self._control_surface = control_surface
        self._track = self.song().view.selected_track
        self._track_devices = self._track.devices
        self._on_device_changed.subject = self.song()
        return

    def disconnect(self):
        self._track_devices = None
        self._track = None
        self._control_surface = None
        super(AltDeviceComponent, self).disconnect()
        return

    def _lock_value(self, value):
        if self._lock_button == None: raise AssertionError
        if value == None: raise AssertionError
        if not isinstance(value, int): raise AssertionError
        if self._device != None and (not self._lock_button.is_momentary() or value is not 0):
            self._locked_to_device = not self._locked_to_device
            self._update_lock_button()
            self._on_device_changed()
            if self._locked_to_device:
                self._show_msg_callback('Locked to Secondary Device Controls')
            else:
                self._show_msg_callback('Unlocked from Secondary Device Controls')
        return

    def on_enabled_changed(self):
        if self._control_surface != None:
            self._control_surface.schedule_message(1, self._update_device_selection)
        else:
            self.update()

    def on_selected_track_changed(self):
        if self._locked_to_device == False and self._control_surface._device_selection_follows_track_selection:
            self._track = self.song().view.selected_track
            self._track_devices = self._track.devices
            self._on_device_list_changed.subject = self._track
            if self.is_enabled():
                self._control_surface.schedule_message(1, self._update_device_selection)

    @subject_slot('appointed_device')
    def _on_device_changed(self):
        if self.is_enabled():
            if self._locked_to_device == False:
                self._update_device_selection()

    @subject_slot('devices')
    def _on_device_list_changed(self):
        self._track_devices = self._track.devices
        if not self._device in self._track_devices:
            self._locked_to_device = False
            if self.is_enabled():
                self._update_device_selection()

    def _update_device_selection(self):
        if len(self._track_devices) > 0:
            self.set_device(self.song().appointed_device)
        else:
            self.set_device(None)
        return