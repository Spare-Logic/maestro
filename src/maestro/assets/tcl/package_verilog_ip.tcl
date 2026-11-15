# SPDX-FileCopyrightText: 2026 Maestro authors and contributors
# SPDX-FileContributor: Cedric Hirschi <cedr02@live.com>
# SPDX-FileContributor: Tim Frey <timfreyb@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

# Package a Verilog/SystemVerilog top as a Vivado user IP (component.xml + xgui).
#
# Uses the built-in ipx:: packager (UG1118). Bus interfaces are inferred from
# (* X_INTERFACE_INFO = "..." *) attributes on the top module ports.
#
# Tclargs (fixed order, then one path per RTL file):
#   <ip_name> <top_module> <ip_out_dir> <work_dir> <vendor> <library> <version> \
#     <part> <ip_repo_paths> <source_0> [<source_1> ...]
#
#   ip_repo_paths: semicolon-separated Vivado IP repository directories, or - for none
#
# Example:
#   vivado -mode batch -notrace -source package_verilog_ip.tcl -tclargs \
#     design design_top \
#     design/ip \
#     Projects/design user.org user 1.0 xck26-sfvc784-2LV-c \
#     ip;src/ip \
#     rtl/design_top.v ...

set nargs [llength $argv]
if {$nargs < 10} {
    puts "Usage: vivado -mode batch -source package_verilog_ip.tcl -tclargs \\"
    puts "         <ip_name> <top_module> <ip_out_dir> <work_dir> \\"
    puts "         <vendor> <library> <version> <part> <ip_repo_paths> \\"
    puts "         <source_0> \[<source_1> ...\]"
    exit 1
}

set ip_name     [lindex $argv 0]
set top_module  [lindex $argv 1]
set ip_out_dir  [file normalize [lindex $argv 2]]
set work_dir    [file normalize [lindex $argv 3]]
set ip_vendor   [lindex $argv 4]
set ip_library  [lindex $argv 5]
set ip_version  [lindex $argv 6]
set part        [lindex $argv 7]
set ip_repo_paths [lindex $argv 8]
set src_files   [lrange $argv 9 end]

if {[llength $src_files] == 0} {
    puts "ERROR: no source files"
    exit 1
}

proc xgui_tcl_path {ip_root core_name core_version} {
    set ver_suffix [string map {. _} $core_version]
    return [file join $ip_root xgui ${core_name}_v${ver_suffix}.tcl]
}

proc remove_core_xgui_files {core} {
    foreach group [ipx::get_file_groups -of_objects $core] {
        if {![string match xilinx_xpgui* [get_property NAME $group]]} {
            continue
        }
        foreach f [ipx::get_files -of_objects $group] {
            ipx::remove_file $f $group
        }
    }
}

proc cleanup_stale_xgui_files {ip_root keep_path} {
    set xgui_dir [file join $ip_root xgui]
    if {![file isdirectory $xgui_dir]} {
        return
    }
    set keep_norm [file normalize $keep_path]
    foreach path [glob -nocomplain -directory $xgui_dir *.tcl] {
        if {[file normalize $path] ne $keep_norm} {
            file delete -force $path
        }
    }
}

puts "Packaging $top_module as $ip_name ([llength $src_files] files) -> $ip_out_dir"

file mkdir $work_dir
cd $work_dir

set proj_name ip_package_$ip_name
if {[file exists ${proj_name}.xpr]} {
    file delete -force ${proj_name}.xpr ${proj_name}.cache ${proj_name}.runs ${proj_name}.srcs
}

create_project $proj_name . -part $part -force
set_property target_language Verilog [current_project]

if {$ip_repo_paths ne "-"} {
    set repos {}
    foreach r [split $ip_repo_paths ";"] {
        if {$r ne ""} {
            lappend repos [file normalize $r]
        }
    }
    if {[llength $repos] > 0} {
        set_property ip_repo_paths $repos [current_fileset]
        puts "IP repo paths: $repos"
    }
}

foreach f $src_files {
    if {![file exists $f]} {
        puts "ERROR: missing source $f"
        exit 1
    }
    set ext [string tolower [file extension $f]]
    if {$ext eq ".sv"} {
        add_files -norecurse $f
        set_property file_type SystemVerilog [get_files $f]
    } else {
        add_files -norecurse $f
    }
}
update_compile_order -fileset sources_1
set_property top $top_module [current_fileset]

file mkdir $ip_out_dir
ipx::package_project -root_dir $ip_out_dir -vendor $ip_vendor -library $ip_library -taxonomy /UserIP

set core [ipx::current_core]
# package_project creates xgui/<top>_v<ver>.tcl before VLNV is customized.
set stale_xgui [xgui_tcl_path $ip_out_dir [get_property name $core] [get_property version $core]]

set_property name $ip_name $core
set_property version $ip_version $core
set_property display_name $ip_name $core
set_property description "Packaged IP $ip_name v$ip_version (top $top_module)" $core

catch {ipx::infer_bus_interface -all $core}

remove_core_xgui_files $core
if {[file exists $stale_xgui]} {
    file delete -force $stale_xgui
}

ipx::create_xgui_files $core
set xgui_tcl [xgui_tcl_path $ip_out_dir $ip_name $ip_version]
cleanup_stale_xgui_files $ip_out_dir $xgui_tcl

ipx::update_checksums $core
ipx::save_core $core
ipx::unload_core $core

puts "Done: [file join $ip_out_dir component.xml]"
close_project
exit 0
