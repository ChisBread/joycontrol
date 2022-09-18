
class FlashMemory:
    def __init__(self, spi_flash_memory_data=None, default_stick_cal=False, size=0x80000,
            is_pro=True, sncode='CHIS-JOY-930720',
            color_body = [0x32, 0x32, 0x32], color_buttons = [0xAA, 0xAA, 0xAA],
            color_left = [0x82, 0x82, 0x82], color_right = [0x82, 0x82, 0x82]):
        """
        :param spi_flash_memory_data: data from a memory dump (can be created using dump_spi_flash.py).
        :param default_stick_cal: If True, override stick calibration bytes with factory default
        :param size of the memory dump, should be constant
        """
        if spi_flash_memory_data is None:
            spi_flash_memory_data = [0xFF] * size  # Blank data is all 0xFF
            default_stick_cal = True

        if len(spi_flash_memory_data) != size:
            raise ValueError(f'Given data size {len(spi_flash_memory_data)} does not match size {size}.')
        if isinstance(spi_flash_memory_data, bytes):
            spi_flash_memory_data = list(spi_flash_memory_data)

        # set default controller stick calibration
        if default_stick_cal:
            if sncode:
                snsize = 15 if len(sncode) > 15 else len(sncode)
                spi_flash_memory_data[0x6000:0x6011] = list(map(ord,sncode))+[0x00]*(15-len(sncode))
            else:
                spi_flash_memory_data[0x6000] = 0x80
            if is_pro:
                spi_flash_memory_data[0x6012] = 0x03
            spi_flash_memory_data[0x6012] = 0xA0
            # custom color
            spi_flash_memory_data[0x601B] = 0x02
            # L-stick factory calibration
            spi_flash_memory_data[0x603D:0x6046] = [0x00, 0x07, 0x70, 0x00, 0x08, 0x80, 0x00, 0x07, 0x70]
            # R-stick factory calibration
            spi_flash_memory_data[0x6046:0x604F] = [0x00, 0x08, 0x80, 0x00, 0x07, 0x70, 0x00, 0x07, 0x70]
            
            spi_flash_memory_data[0x6050:0x605D] = color_body + color_buttons + color_left + color_right
        self.data = spi_flash_memory_data

    def __getitem__(self, item):
        return self.data[item]

    def get_factory_l_stick_calibration(self):
        """
        :returns 9 left stick factory calibration bytes
        """
        return self.data[0x603D:0x6046]

    def get_factory_r_stick_calibration(self):
        """
        :returns 9 right stick factory calibration bytes
        """
        return self.data[0x6046:0x604F]

    def get_user_l_stick_calibration(self):
        """
        :returns 9 left stick user calibration bytes if the data is available, otherwise None
        """
        # check if calibration data is available:
        if self.data[0x8010] == 0xB2 and self.data[0x8011] == 0xA1:
            return self.data[0x8012:0x801B]
        else:
            return None

    def get_user_r_stick_calibration(self):
        """
        :returns 9 right stick user calibration bytes if the data is available, otherwise None
        """
        # check if calibration data is available:
        if self.data[0x801B] == 0xB2 and self.data[0x801C] == 0xA1:
            return self.data[0x801D:0x8026]
        else:
            return None
