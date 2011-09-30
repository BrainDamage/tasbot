#!/usr/bin/perl -w
#@Author: bibim
use strict;

if($#ARGV < 0) {
  print "Usage: $0 <ProtocolDescription.xml>\n";
  exit 1;
}

if(! -e $ARGV[0]) {
  print "File $ARGV[0] not found\n";
  exit 1;
}

if(! open(XML,"<$ARGV[0]")) {
  print "Unable to open file $ARGV[0]\n";
  exit 1;
}

my %commands;
while(<XML>) {
  if(/command\s+name="(.+)".*source="(.+)"/i) {
    my ($c,$s)=(lc($1),lc($2));
    $commands{$s}=[] unless(defined($commands{$s}));
    push(@{$commands{$s}},$c);
  }
}

foreach my $s (keys %commands) {
  print "Source: $s\n";
  my @c=sort(@{$commands{$s}});
  foreach my $command (@c) {
    print "  $command\n";
  }
}
