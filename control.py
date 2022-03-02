import smbus
import time


# Address	Function
# 00H	Zoom steps
# 01H	Focus steps
# 02H	Zoom speed
# 03H	Focus speed
# 04H	Lens motor state
# 05H	ServoX angle values
# 06H	ServoY angle values
# 07H	Zoom max value
# 08H	Focus max value
# 0AH	Reset the zoom
# 0BH	Reset the focus
# 0CH	IR cut control

class Controller(object):
    
    ZOOM_STEP_REG = 0x00
    FOCUS_STEP_REG = 0x01
    ZOOM_SPEED_REG = 0x02
    FOCUS_SPEED_REG = 0x03
    LENS_MOTOR_STATE_REG = 0x04
    SERVO_PAN_REG = 0x05
    SERVO_TILT_REG = 0x06
    MAX_ZOOM_REG = 0x07
    MAX_FOCUS_REG = 0x08
    RESET_ZOOM_REG = 0x0A
    RESET_FOCUS_REG = 0x0B
    IR_CUT_REG = 0x0C

    BUSY_REG = 0x04

    
    MIN_FOCUS = 1000
    MIN_ZOOM = 3500

    def __init__(self, bus, addr=0x0C):
        self.bus = smbus.SMBus(bus)
        self.addr = addr
        self.max_zoom = self.get_max_zoom()
        self.max_focus = self.get_max_focus()

    def _bswap(self,num: int):
        return (num&0x00FF)<<8 | (num&0xFF00)>>8 

    def is_busy(self):
        return self.bus.read_word_data(self.addr, self.BUSY_REG) != 0

    def waiting_for_free(self):
        count = 0
        while self.is_busy() and count < (5 / 0.01):
            count += 1
            time.sleep(0.01)

    def read_reg(self,reg):
        self.waiting_for_free()
        data = self.bus.read_word_data(self.addr,reg)
        return self._bswap(data)

    def write_reg(self,reg,val):
        self.waiting_for_free()
        if val < 0:
            val = 0
        self.bus.write_word_data(self.addr,reg,self._bswap(val))

    def get_zoom(self):
        return 1-(self.read_reg(self.ZOOM_STEP_REG)-self.MIN_ZOOM)/(self.max_zoom-self.MIN_ZOOM)

    def set_zoom(self,zoom: float):
        if zoom < 0 or zoom > 1:
            raise ValueError("Zoom must be in (0,1)")
        self.write_reg(self.ZOOM_STEP_REG,int((1-zoom)*(self.max_zoom-self.MIN_ZOOM)+self.MIN_ZOOM))

    def get_focus(self):
        return (self.read_reg(self.FOCUS_STEP_REG)-self.MIN_FOCUS)/(self.max_focus-self.MIN_FOCUS)

    def set_focus(self,focus: float):
        if focus < 0:
            print(f"Focus {focus} adjusting to 0")
            focus = 0
        if focus > 1:
            print(f"Focus {focus} adjusting to 1")
            focus = 1
        self.write_reg(self.FOCUS_STEP_REG,int(focus*(self.max_focus-self.MIN_FOCUS)+self.MIN_FOCUS))

    def get_zoom_speed(self):
        return self.read_reg(self.ZOOM_SPEED_REG)

    def get_focus_speed(self):
        return self.read_reg(self.FOCUS_SPEED_REG)

    def get_pan(self):
        return self.read_reg(self.SERVO_PAN_REG)

    def set_pan(self,angle):
        if angle < 0 or angle > 180:
            raise ValueError("Angle must be in (0,180))")
        self.write_reg(self.SERVO_PAN_REG,angle)

    def get_tilt(self):
        return self.read_reg(self.SERVO_TILT_REG)

    def set_tilt(self,angle):
        if angle < 15 or angle > 170:
            raise ValueError("Angle must be in (0,180))")
        self.write_reg(self.SERVO_TILT_REG,angle)

    def get_max_zoom(self):
        return self.read_reg(self.MAX_ZOOM_REG)

    def get_max_focus(self):
        return self.read_reg(self.MAX_FOCUS_REG)

    def get_ir_cut(self):
        return self.read_reg(self.IR_CUT_REG)

    def ir_no_pass(self):
        self.write_reg(self.IR_CUT_REG,0)

    def ir_pass(self):
        self.write_reg(self.IR_CUT_REG,1)





    def print_status(self):
        print(f"""Zoom: {self.get_zoom()} (max: {self.get_max_zoom()}, speed: {self.get_zoom_speed()})
Focus: {self.get_focus()} (max: {self.get_max_focus()}, speed: {self.get_focus_speed()})
Pan: {self.get_pan()}, tilt:{self.get_tilt()}
IR Cut: {self.get_ir_cut()}
        """)
