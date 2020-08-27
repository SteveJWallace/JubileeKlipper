class Dock:
    def __init__(self, config): 
        self.printer          = config.get_printer()
        self.gcode   = self.printer.lookup_object('gcode') 
        self.parking_location = {"0.0", "0.0", "0.0"}
        self.zone_location    = {"0.0", "0.0", "0.0"}
        self.parking_speed    = config.getint('parking_speed', 1000)
        self.travel_speed     = config.getint('travel_speed',2000)
        self.tool_offset      = {"0.0", "0.0", "0.0"}
        self.tool_present     = False
        self.gcode.register_command('BETA_TOOL_DROPOFF', self.cmd_TOOL_DROPOFF,
                                   desc=self.cmd_TOOL_DROPOFF_help)
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