Jubilee on Klipper
=======
##Overview
The goal of this project is to enable people building Jubilee tool changers to use Klipper firmware and commodity electronics to build a very capable and advanced tool changing 3d printer.

1. What is Jubilee?
Jubilee is an open-source, extensible multi-tool motion platform capable of running GCode for non-loadbearing automation applications. Most commmonly it use used as a tool changing 3d printer with up to five tools. But it has been used for things such as light liquid handling, image stitching, pen plotting etc.
[Jubilee on Github](https://github.com/machineagency/jubilee)
[Jubilee Wiki](https://jubilee3d.com/index.php?title=Main_Page)

2. What is Klipper?
Klipper is a firmware used for 3D Printers, one of its great strengths lies in the ability to combine commodity computers and microcontrollers to create very advanced printers. I would suggest reading through the [features document](https://www.klipper3d.org/Features.html) for more
information on why you should use Klipper. 
[Klipper on Github](https://github.com/KevinOConnor/klipper)


##Custom gcode commands.
1. Tool Locking
   The tool locking macros are specific to the Jubilee lock mechanism. They are contained in a seperate macro file and need to be added to your config using an include section in your main config.
   ~~~
   [include toollock.cfg]
   ~~~
   These macros expect that you have configured a manual stepper named *tool_lock*.
   Your machine config should contain something like the following..
   ~~~
   [manual_stepper tool_lock]
   step_pin: PE13
   dir_pin: PC2
   enable_pin: !PC0
   step_distance: .005
   endstop_pin: PG8
   ~~~
   This defines a manual stepper and an endstop, this is the one with two switches on the tool carrier. *The tool lock macros can be found in [configs/toollock.cfg](/configs/toollock.cfg
   1. LOCK_INIT
   This needs to be called as part of your printers initialization, its sets up variables to track the locks status as well moves the lock into a known state.
   2. TOOL_LOCK
   This turns the jubilee twist lock into the locked position. It does this by moving a small amount until the endstop is disengaged and then moving until it is fully engaged again. You might have to tune the distances slightly based on which geared stepper motor you have, mine is based on the original 5:1 geared stepper from Steppers Online that was specifed in the Jubilee 1.0 bill of materials. This macro will not take any action if it believes it is already locked.
   3. TOOL_UNLOCK
   This turns the twist lock into the unlocked position in the same manner as previous operation
2. Tool Docking
    The tool dock macros move to a tool zone and then into a park zone to either engage or disengage the lock using the TOOL_LOCK and TOOL_LOCK macros. Additionally they save the zones, track whether or not a tool is in place and they also enforce safety checks like making sure that you drop off a tool before picking a new one up or making sure the lock is unlocked before trying to pickup a tool.

    *The tool lock macros can be found in [configs/tooldock.cfg](/configs/tooldock.cfg)*
    1. DOCK_INIT
        Just like tool init you need to add this to your 
        ~~~
        [include tooldock.cfg]
        ~~~
    2. TOOL_PICKUP
    This macro takes a set of parameters that define the docking and park zone and tool offsets. If there is a tool in place it will move to the previous tool zone then to the park zone, unlock the tool and then back to to tool zone leaving it on the dock. It will then move to the provided tool zone continue to the park zone and lock the tool in place before returning to the tool zone and returning to the original location of the tool. This macro also applies the tool offsets provided.
        ```
        TOOL_PICKUP ZONE_X=5 ZONE_Y=260 PARK_X=5 PARK_Y=341 OFFSET_X=4.5 OFFSET_Y=-44.02 OFFSET_Z=2.65
        ```   
   3. TOOL_DROPOFF
   If a tool is in place TOOL_DROPOFF will return it to the tool dock that it was initially picked up from and park the tool carriage at the tool zone and reset any tool offsets applied when the tool was picked up.
   4. TOOL_HOME
   This macro allows you to alter the location that the tool is returned to after a tool change is complete. Why would you want to do this? Most of the time your tool will return to the printing area, but if your using a prime tower you might want it to go there first to reduce the number of travels and reduce stringing. 
3. Utilities & Helpers
   1. G28
    I've added a safety check to prevent accidentally homing the tool carriage if a tool is in place, on the Jubilee doing so will fail because the fan block the endstop switch. 
   2. Fans
    The default implementation of M106 and M107 in Klipper does not support multiple fans. So I've provided one that can be added by including *[configs/fans.cfg](/configs/fans.cfg) in your printer config via an include.
        ~~~
        [include fans.cfg]
        ~~~
        Additionally you will need to add a pin that can be PWM controlled for each additional fan.
        ~~~
        [output_pin tool2_fan]
        pin: PE5
        pwm:true
        ~~~
        If you want additional fans you will need to add additional PWM outputs and modify the part of the M106 macro that selects the fan...
        ~~~
        {% if P == 0 %}
            M106.1 S{ S }
        #If you need more fans copy the logic below for each additional fan.
        {% elif P == 1 %}
            SET_PIN PIN=tool2_fan VALUE={ S/255.0 } 
        {% endif %} 
        ~~~
        to something like this
        ~~~
        {% if P == 0 %}
            M106.1 S{ S }
        #If you need more fans copy the logic below for each additional fan.
        {% elif P == 1 %}
            SET_PIN PIN=tool2_fan VALUE={ S/255.0 } 
        {% elif P == 2 %}
            SET_PIN PIN=tool3_fan VALUE={ S/255.0 }
        {% endif %} 
        ~~~
        and for M107 you need to make changes to 
        ~~~
        {% if P == 0 %}
            M107.1
        {% elif P == 1 %}
            SET_PIN PIN=tool2_fan VALUE=0 
        {% endif %} 
        ~~~
        to something like
        ~~~
        {% if P == 0 %}
            M107.1
        {% elif P == 1 %}
            SET_PIN PIN=tool2_fan VALUE=0 
        {% elif P == 2 %}
            SET_PIN PIN=tool3_fan VALUE=0 
        {% endif %} 
    3. Idle Timeout
    The idle timeout I've provided in the sample config turns off the motors, heaters and fans. It also returns any tool it has back into its dock or unlocks the twistlock if it is locked. 

##Sample Printer Config
###Overview
I've provided a sample Klipper config based on two BigTree Tech SKR Pro 1.1 boards. The main board handles the X,Y, Twist lock steppers & end stops as well as an extruder. The second board handles Z1,Z2,Z3 and an extruder as well as the heated bed's SSR and the z endstop switch on the tool carriage. I plan on documenting more as I have time. 

*The sample printer config can be found in  [/configs/printer-jubilee-skr-pro.cfg](/configs/printer-jubilee-skr-pro.cfg)*
Sample printer initialization...
```
[gcode_macro INIT]
gcode:
    {% if not printer["gcode_macro DOCK_INIT"].tool_present %}
        g28
        Z_TILT_ADJUST
        g1 X10 Y10 F3000
        LOCK_INIT
        DOCK_INIT
    {% else %}
        { printer.gcode.action_respond_info("You cannot run INIT with a tool in place, please run TOOL_UNLOCK and manually place the tool in its dock.") }
    {% endif %}

```

Example of what the T0 macro looks like. 
```
[gcode_macro T0]
gcode:
	TOOL_PICKUP ZONE_X=5 ZONE_Y=260 PARK_X=5 PARK_Y=341 OFFSET_X=4.5 OFFSET_Y=-44.02 OFFSET_Z=2.65
	ACTIVATE_EXTRUDER EXTRUDER=extruder
```
###Performance & Tuning
    TBD..
##Slicer Support
At this time this has only been tested using Cura 3.6.0 and Cura 4.6.2. There is at least one bug that causes print failure in Cura 4.x currently. Essentially the issue has to do with Cura making moves to X0 Y0 with tools that cannot reach the location due to tool offsets.

####Using it with Cura 4.6

#####What to do about Cura's bug?
Currently I simply search for X0.00 Y0.00 in the gcode file after slicing and comment it out. While this is not the greatest solution the only other option is to move back to Cura 3.6.