import logging

class Tool:
    def __init__(self, config):        
        self.config  = config
        self.printer = config.get_printer()       
        self.name    = config.get_name().split()[1]
        self.gcode   = self.printer.lookup_object('gcode') 
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.dock    = self.printer.load_object(config, 'dock')
        #read the config..     
        self.parking_location = [ float(i) for i in config.get('parking_location').split(',')]
        self.zone_location    = [ float(i) for i in config.get('zone_location').split(',')]
        self.offset           = [ float(i) for i in config.get('offset').split(',')]
        self.approach_path    = self._getPoints(config.get('approach_path',''))
        self.return_path      = self._getPoints(config.get('return_path',''))
        #if we dont have a return path, reverse the approach
        if len(self.return_path)==0:
            self.return_path = self.approach_path[::-1]          
        #read the templates for the tool
        #read the temmplates for the tool
        if config.get('lock_gcode', None) is not None:
            self.tool_lock  =  gcode_macro.load_template(config, 'lock_gcode',None)
        else:
            logging.info('using the docks lock macro')
            self.tool_lock  = self.dock.tool_lock
        if config.get('unlock_gcode', None) is not None:
            self.tool_unlock  =  gcode_macro.load_template(config, 'unlock_gcode',None)
        else:
            logging.info('using the docks unlock macro')
            self.tool_unlock  = self.dock.tool_unlock
        self.pre_zone  =  gcode_macro.load_template(config, 'pre_zone_gcode','')
        self.post_zone =  gcode_macro.load_template(config, 'post_zone_gcode', '')
        self.pre_park  =  gcode_macro.load_template(config, 'pre_park_gcode', '')
        self.post_park =  gcode_macro.load_template(config, 'post_park_gcode', '')
        self.gcode.register_mux_command(
            "BETA_TOOL_PICKUP", "TOOL", self.name,
            self.cmd_TOOL_PICKUP,
            desc=self.cmd_TOOL_PICKUP_help)
        #Replacement for original logic.
        self.gcode.register_mux_command(
            "BETA_TOOL_PICKUP_2", "TOOL", self.name,
            self.cmd_TOOL_PICKUP_ADV,
            desc=self.cmd_TOOL_PICKUP_ADV_help)            

    def _getPoints(self, lines):
        points=[]
        for line in  lines.strip().split('\n'):
            if not line=="":
                point={}
                for param in  line.split(' '):
                    try:
                        point[param[0]]= float(param[1:])
                    except Exception:
                        logging.exception("Error in [tool " + self.name + "], param:" + param + " from  line:" + line) 
                points.append (point)
        return points

    def get_status(self, eventtime):
        return dict( approach_path = self.approach_path,
            return_path = self.return_path,
            tool_lock = self.tool_lock,
            tool_unlock = self.tool_unlock,
            pre_zone_gcode = self.pre_zone,
            post_zone_gcode = self.post_zone,
            pre_park_gcode = self.pre_park,
            post_park_gcode = self.post_park
        )

    cmd_TOOL_PICKUP_help= "Pick up a tool from the dock"
    def cmd_TOOL_PICKUP(self, gcmd):
         if self.dock.tool_present:
             self.dock.cmd_TOOL_DROPOFF(gcmd)
         #dropoff the tool if we have one.
         self.dock.cmd_TOOL_DROPOFF(gcmd)
         self._exec(self.pre_zone)
         #move to the tool pickup zone
         self.dock.move(self.zone_location, self.dock.travel_speed, gcmd)
         #move to the parking zone.
         self.dock.move(self.parking_location, self.dock.parking_speed, gcmd)
         self._exec(self.tool_lock)
         #move back to the pickup zone
         self.dock.move(self.zone_location, self.dock.travel_speed, gcmd)
         #apply the users offset
         self.dock.set_gcode_offset(self.offset)
         self._exec(self.post_zone)
         #Save the location of the tool so dropoff knows what to do later.
         self.dock.parking_location = self.parking_location
         self.dock.zone_location    = self.zone_location
         self.dock.tool_offset      = self.offset
         self.dock.tool_present     = True
         #move back to origin?
         gcmd.respond_info('prior state:"%s"'
            % (self.dock.tool_present,))

    cmd_TOOL_PICKUP_ADV_help= "Pick up a tool from the dock, using paths"
    def cmd_TOOL_PICKUP_ADV(self, gcmd):
         if self.dock.tool_present:
             self.dock.cmd_TOOL_DROPOFF(gcmd)
         else:
             self._exec(self.tool_unlock)
         self._exec(self.pre_zone)
         #Loop though approach_path
         for move in self.approach_path:
             self.dock._extractMove(move)
         #Lock the tool
         self._exec(self.tool_lock)
         #Loop though return_path
         for move in self.return_path:
             self.dock._extractMove(move)
         #apply the users offset
         self.dock.set_gcode_offset(self.offset)
         self._exec(self.post_zone)
         #Save the location of the tool so dropoff knows what to do later.
         self.dock.parking_location = self.parking_location
         self.dock.zone_location    = self.zone_location
         #Save the offset so we can reverse it later. 
         self.dock.tool_offset      = self.offset
         #Indicate tool presence.
         self.dock.tool_present     = True
         #move back to origin?
         gcmd.respond_info('prior state:"%s"'
            % (self.dock.tool_present,))

    def _exec(self, script):
        try:
            self.gcode.run_script_from_command(script.render())
        except Exception:
            logging.exception("Script running error")

def load_config_prefix(config):
    return Tool(config)