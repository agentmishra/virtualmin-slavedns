#!/usr/local/bin/perl
# Update master server IPs

require 'virtualmin-slavedns-lib.pl';
&ReadParse();
&error_setup($text{'save_err'});

if ($in{'adv'}) {
	# Redirect to BIND module
	&redirect("../bind8/edit_slave.cgi?zone=$in{'dom'}");
	return;
	}

# Get and check the domain
&can_edit_slave($in{'dom'}) || &error($text{'edit_ecannot'});
$d = &virtual_server::get_domain_by("dom", $in{'dom'});
if (defined(&virtual_server::obtain_lock_dns)) {
	&virtual_server::obtain_lock_dns($d, 1);
	}
$z = &virtual_server::get_bind_zone($in{'dom'});
$z || &error($text{'edit_ezone'});
$rfile = &bind8::find('file', $z->{'members'});
&virtual_server::require_bind();

# Validate inputs
@mips = split(/\s+/, $in{'master'});
foreach $ip (@mips) {
	&check_ipaddress($ip) || &error(&text('save_emip', $ip));
	}
@mips || &error($text{'save_emips'});

# Run the before command
&virtual_server::set_domain_envs($d, "MODIFY_DOMAIN", $d);
$merr = &virtual_server::making_changes();
&virtual_server::reset_domain_envs($d);
&error(&virtual_server::text('save_emaking', "<tt>$merr</tt>"))
	if (defined($merr));

&ui_print_unbuffered_header(&virtual_server::domain_in($d),
			    $text{'edit_title'}, "");

# Update the .conf file
&$virtual_server::first_print($text{'save_doing'});
$masters = &bind8::find('masters', $z->{'members'});
$oldmasters = { %$masters };
$masters->{'members'} = [ map { { 'name' => $_ } } @mips ];
&bind8::save_directive($z, [ $oldmasters ], [ $masters ], 1);
$allow = &bind8::find('allow-notify', $z->{'members'});
if ($allow) {
	$oldallow = { %$allow };
	$allow->{'members'} = [ map { { 'name' => $_ } } @mips ];
	&bind8::save_directive($z, [ $oldallow ], [ $allow ], 1);
	}
&flush_file_lines($z->{'file'});
&$virtual_server::second_print($virtual_server::text{'setup_done'});

# Clear the zone file, to force a re-transfer
if ($rfile) {
	$rfilev = $rfile->{'value'};
	&open_tempfile(ZONE, ">".&bind8::make_chroot($rfilev), 0, 1);
	&close_tempfile(ZONE);
	&bind8::set_ownership(&bind8::make_chroot($rfilev));
	}
if (&bind8::is_bind_running()) {
	&bind8::stop_bind();
	&bind8::start_bind();
	}

# Run the after command
&virtual_server::set_domain_envs($d, "MODIFY_DOMAIN", undef, $d);
$merr = &virtual_server::made_changes();
&$virtual_server::second_print(
	&virtual_server::text('setup_emade', "<tt>$merr</tt>"))
	if (defined($merr));
&virtual_server::reset_domain_envs($d);

if (defined(&virtual_server::release_lock_dns)) {
	&virtual_server::release_lock_dns($d, 1);
	}
&webmin_log("save", undef, $in{'dom'});

&ui_print_footer("edit.cgi?dom=$in{'dom'}", $text{'edit_return'});

