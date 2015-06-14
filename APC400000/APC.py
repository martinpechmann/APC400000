import Live
from _APC.APC import APC as APCBase

class APC(APCBase):

    def disconnect(self):
        self._do_uncombine()
        super(APCBase, self).disconnect()
        self._send_midi((240,
         71,
         self._device_id,
         self._product_model_id_byte(),
         96,
         0,
         4,
         64,
         self.application().get_major_version(),
         self.application().get_minor_version(),
         self.application().get_bugfix_version(),
         247))