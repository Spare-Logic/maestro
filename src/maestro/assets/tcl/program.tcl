# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

# TCL script to program an FPGA using Vivado Hardware Manager
# Arguments:
# 1. bitfile path
# 2. device name (optional, default: xck26_0)

# Get the bitfile from command line arguments
puts $argv
set file [lindex $argv 0]

# Get the device name from command line arguments
set device [lindex $argv 1]
if {![info exists device]} {
    set device {xck26_0}
}

open_hw_manager
connect_hw_server
open_hw_target
puts [get_hw_devices]

# Connect to device
puts "Connecting to device $device"

current_hw_device [get_hw_devices $device]
refresh_hw_device -update_hw_probes false [lindex [get_hw_devices $device] 0]


# check if file exists
if {![file exists $file]} {
    puts "Error: File $file does not exist."

    set file bin/${file}/${file}.bit
    if {![file exists $file]} {
        puts "Error: File $file does not exist."
        exit 1
    } else {
        puts "Using alternative file path: $file"
    }
}

# .ltx file ??
set ltx_file [file rootname $file].ltx
if {[file exists $ltx_file]} {
    puts "Found LTX file: $ltx_file"
    set_property PROBES.FILE $ltx_file [get_hw_devices $device]
} else {
    puts "No LTX file found for $file"
    set_property PROBES.FILE {} [get_hw_devices $device]
}

set_property PROGRAM.FILE $file [get_hw_devices $device]

program_hw_devices [get_hw_devices $device]
refresh_hw_device [lindex [get_hw_devices $device] 0]
close_hw_target

puts ""
puts "Done programming $file"
puts "  to $device"
