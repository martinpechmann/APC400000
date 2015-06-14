from _Framework.ModesComponent import ModesComponent
from _Framework.SubjectSlot import subject_slot

class LatchingToggleModesComponent(ModesComponent):

    @subject_slot('value')
    def _on_toggle_value(self, value):
        if self._shift_button:
            shift = self._shift_button.is_pressed()
            if not shift and self.is_enabled() and len(self._mode_list):
                is_press = value and not self._last_toggle_value
                is_release = not value and self._last_toggle_value
                can_latch = self._mode_toggle_task.is_killed and len(self._mode_list) > 1
                (not self._mode_toggle.is_momentary() or is_press) and self.cycle_mode(1)
                self._mode_toggle_task.restart()
                if is_release and (self.momentary_toggle or can_latch):
                    self.cycle_mode(-1)
            self._last_toggle_value = value