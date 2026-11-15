# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

# JTAG AXI batch. tclargs: <device> <hw_axi> <read|write> <addr_hex> ...
#   read  <addr>
#   write <addr> <data>
# Prints "AXI_READ <hex>" after each read.
# On a transaction error whose text contains "failed" or "timeout", exits with an error.

set device [lindex $argv 0]
if {$device eq ""} { set device xck26_0 }

set hw_axi_name [lindex $argv 1]
if {$hw_axi_name eq ""} { set hw_axi_name hw_axi_1}

open_hw_manager
connect_hw_server
open_hw_target

current_hw_device [get_hw_devices $device]
refresh_hw_device [lindex [get_hw_devices $device] 0]

set hw_axi [get_hw_axis $hw_axi_name]
reset_hw_axi $hw_axi

set i 2
set n 0
set order {}

while {$i < [llength $argv]} {
    set op [string tolower [lindex $argv $i]]
    incr i
    set addr [format %08x [scan [lindex $argv $i] %x]]
    incr i

    set name t$n
    incr n

    if {$op eq "read"} {
        create_hw_axi_txn $name $hw_axi -type read -address $addr
    } elseif {$op eq "write"} {
        set data [lindex $argv $i]
        incr i
        create_hw_axi_txn $name $hw_axi -type write -address $addr -data $data
    } else {
        error "expected read or write, got: $op"
    }
    lappend order $name
}

foreach name $order {
    set txn [get_hw_axi_txns $name]
    if {[catch {run_hw_axi $txn} msg]} {
        set detail "$msg\n$::errorInfo"
        catch {close_hw_target}
        # An unclocked or unreleased port shows up as "failed" or "timeout".
        if {[string match -nocase *failed* $detail]
            || [string match -nocase *timeout* $detail]} {
            set addr ""
            catch {set addr [get_property ADDRESS $txn]}
            error "AXI transaction at $addr failed: clock or reset may not be configured correctly"
        }
        error $msg
    }
    if {[string tolower [get_property TYPE $txn]] eq "read"} {
        puts "AXI_READ [get_property DATA $txn]"
    }
}

close_hw_target
