<?php

# This file was automatically generated by the MediaWiki installer.
# If you make manual changes, please keep track in case you need to
# recreate them later.
#
# See includes/DefaultSettings.php for all configurable settings
# and their default values, but don't forget to make changes in _this_
# file, not there.
#
# Further documentation for configuration settings may be found at:
# http://www.mediawiki.org/wiki/Manual:Configuration_settings

# If you customize your file layout, set $IP to the directory that contains
# the other MediaWiki files. It will be used as a base to locate files.
if( defined( 'MW_INSTALL_PATH' ) ) {
	$IP = MW_INSTALL_PATH;
} else {
	$IP = dirname( __FILE__ );
}

$path = array( $IP, "$IP/includes", "$IP/languages" );
set_include_path( implode( PATH_SEPARATOR, $path ) . PATH_SEPARATOR . get_include_path() );

require_once( "$IP/includes/DefaultSettings.php" );

# If PHP's memory limit is very low, some operations may fail.
# ini_set( 'memory_limit', '20M' );

if ( $wgCommandLineMode ) {
	if ( isset( $_SERVER ) && array_key_exists( 'REQUEST_METHOD', $_SERVER ) ) {
		die( "This script must be run from the command line\n" );
	}
}
## Uncomment this to disable output compression
# $wgDisableOutputCompression = true;

$wgSitename         = "Wikipedia";

## The URL base path to the directory containing the wiki;
## defaults for all runtime URL paths are based off of this.
## For more information on customizing the URLs please see:
## http://www.mediawiki.org/wiki/Manual:Short_URL
$wgScriptPath       = "";
$wgScriptExtension  = ".php";

## UPO means: this is also a user preference option

$wgEnableEmail      = false;
$wgEnableUserEmail  = false; # UPO

$wgEmergencyContact = "root@localhost";
$wgPasswordSender = "root@localhost";

$wgEnotifUserTalk = false; # UPO
$wgEnotifWatchlist = false; # UPO
$wgEmailAuthentication = false;

## Database settings
$wgDBtype           = "mysql";
$wgDBserver         = "localhost";
__WIKIUSERSETTINGS__

# MySQL specific settings
$wgDBprefix         = "";

# MySQL table options to use during installation or update
$wgDBTableOptions   = "ENGINE=MyISAM, DEFAULT CHARSET=binary";

# Experimental charset support for MySQL 4.1/5.0.
$wgDBmysql5 = true;

## Shared memory settings
$wgMainCacheType = CACHE_NONE;
$wgMemCachedServers = array();

## To enable image uploads, make sure the 'images' directory
## is writable, then set this to true:
$wgEnableUploads       = true;
$wgUseImageMagick = false;
$wgImageMagickConvertCommand = "/usr/bin/convert";

## If you use ImageMagick (or any other shell command) on a
## Linux server, this will need to be set to the name of an
## available UTF-8 locale
$wgShellLocale = "en_US.utf8";

## If you want to use image uploads under safe mode,
## create the directories images/archive, images/thumb and
## images/temp, and make them all writable. Then uncomment
## this, if it's not already uncommented:
# $wgHashedUploadDirectory = false;

## If you have the appropriate support software installed
## you can enable inline LaTeX equations:
$wgUseTeX           = false;

$wgLocalInterwiki   = strtolower( $wgSitename );
$wgInterwikiMagic = true;
$wgHideInterlanguageLinks = false;



$wgSecretKey = "87a0d23fbd99994a24257c12fda44200cfbb33c5d3dbb2d74fb4e38643f1e639";

## Default skin: you can change the default skin. Use the internal symbolic
## names, ie 'standard', 'nostalgia', 'cologneblue', 'monobook':
$wgDefaultSkin = 'monobook';

## For attaching licensing metadata to pages, and displaying an
## appropriate copyright notice / icon. GNU Free Documentation
## License and Creative Commons licenses are supported so far.
# $wgEnableCreativeCommonsRdf = true;
$wgRightsPage = ""; # Set to the title of a wiki page that describes your license/copyright
$wgRightsUrl = "";
$wgRightsText = "";
$wgRightsIcon = "";
# $wgRightsCode = ""; # Not yet used

$wgDiff3 = "/usr/bin/diff3";

# When you make changes to this configuration file, this will make
# sure that cached pages are cleared.
$wgCacheEpoch = max( $wgCacheEpoch, gmdate( 'YmdHis', @filemtime( __FILE__ ) ) );
$wgGenerateThumbnailOnParse = false;

$wgDefaultUserOptions = array('math' => 4);

$wgUseTidy = true;
$wgTidyBin = '/usr/bin/tidy';
$wgTidyConf = $IP.'/extensions/tidy/tidy.conf';

require( "extensions/ParserFunctions/ParserFunctions.php");
require( "extensions/ImageMap/ImageMap.php");
require( "extensions/Cite/Cite.php");

require( "extensions/SyntaxHighlight_GeSHi/SyntaxHighlight_GeSHi.php");

#$wgForeignFileRepos[] = array(
#   'class'                   => 'ForeignAPIRepo',
#   'name'                    => 'shared',
#   'apibase'                 => 'http://commons.wikimedia.org/w/api.php',
#   'fetchDescription'        => true, // Optional
#   'descriptionCacheExpiry'  => 43200, // 12 hours, optional
#   'apiThumbCacheExpiry'     => 43200, // 12 hours, optional, but required for local thumb caching
#);
$wgForeignFileRepos[] = array(
    'class' => 'ForeignDBRepo',
    'name' => 'commons',
    'url' => "http://upload.wikimedia.org/wikipedia/commons",
    'hashLevels' => 2, // This must be the same for the other family member
    //'thumbScriptUrl' => "http://wiki.example.com/thumb.php",
    'transformVia404' => true,//!$wgGenerateThumbnailOnParse,
    'dbType' => $wgDBtype,
    'dbServer' => $wgDBserver,
    'dbUser' => $wgDBuser,
    'dbPassword' => $wgDBpassword,
    'dbName' => $wgDBname,
    'tablePrefix' => 'commons_',
    'hasSharedCache' => false,
    'descBaseUrl' => 'http://commons.wikimedia.org/wiki/File:',
    'fetchDescription' => false
);
