import logging

class Dock:
    def __init__(self, config): 
        self.printer          = config.get_printer()
        self.printer.add_object("dock", self)
        self.gcode   = self.printer.lookup_object('gcode') 
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.parking_location = {"0.0", "0.0", "0.0"}
        self.zone_location    = {"0.0", "0.0", "0.0"}
        self.parking_speed    = config.getint('parking_speed', 1000)
        self.travel_speed     = config.getint('travel_speed',2000)
        self.tool_lock  =  gcode_macro.load_template(config, 'lock_gcode',None)
        self.tool_unlock  =  gcode_macro.load_template(config, 'unlock_gcode',None)
        self.tool_offset      = {"0.0", "0.0", "0.0"}
        self.tool_present     = False
        self.gcode.register_command('BETA_TOOL_DROPOFF', self.cmd_TOOL_DROPOFF,
                                   desc=self.cmd_TOOL_DROPOFF_help)
    def _exec(self, script):
        try:
            self.gcode.run_script_from_command(script.render())
        except Exception:
            logging.exception("Script running error")

    def move(self, coord, speed, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        curpos = toolhead.get_position()
        for i in range(len(coord)):
            gcmd.respond_info('i:"%i" v:"%i"'% (i,coord[i]),)
            if coord[i] is not None:
                curpos[i] = coord[i]+self.gcode.base_position[i]
        gcmd.respond_info('speed:"%i"'% (speed),)
        toolhead.move(curpos, self.gcode.speed_factor * speed)
        self.gcode.reset_last_position()

    def get_status(self, eventtime):
        return dict(parking_speed = self.parking_speed,
                    travel_speed=self.travel_speed)

    def get_parking_speed(self):
        return self.parking_speed

    def set_gcode_offset(self, offset):
        for i in range(len(offset)):
            delta = offset[i] - self.gcode.homing_position[i]
            self.gcode.base_position[i] += delta
            self.gcode.homing_position[i] = offset[i]        

    cmd_TOOL_DROPOFF_help = "Place a tool back in the dock"
    def cmd_TOOL_DROPOFF(self, gcmd):
         if self.tool_present:
            self.set_gcode_offset([0.,0.,0.])
            self.move(self.zone_location, self.travel_speed, gcmd)
            #move to the parking zone.
            self.move(self.parking_location, self.parking_speed, gcmd)
            self._exec(self.tool_unlock)
            #move back to the pickup zone
            self.move(self.zone_location, self.travel_speed, gcmd)
            #Save the location of the tool so dropoff knows what to do later.
            self.parking_location = [0.0, 0.0]
            self.zone_location    = [0.0, 0.0]
            self.tool_offset      = [0.0, 0.0, 0.0]
            self.tool_present     =False
            gcmd.respond_info('prior state:"%s"'
                % (self.tool_present,))

def load_config(config):
    return Dock(config)