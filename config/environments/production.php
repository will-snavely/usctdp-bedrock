<?php

/**
 * Configuration overrides for WP_ENV === 'production'
 */

use Roots\WPConfig\Config;

use function Env\env;

/**
 * application.php defaults WP_DEBUG_LOG to false, and this was the only
 * environment missing a config/environments/{WP_ENV}.php to override it -
 * gen_bedrock_env.py has always generated a real WP_DEBUG_LOG path here
 * (see WP_LOG in Taskfile.prod.yml and the tail-wp-log task), but nothing
 * ever read it, so nothing was ever writing to web/app/debug.log despite
 * all the tooling built around it. Deliberately only overrides logging -
 * WP_DEBUG and WP_DEBUG_DISPLAY stay off (application.php's production
 * defaults), so this doesn't change what's verbose or what's ever shown
 * on-screen, only whether fatals/warnings get written anywhere at all.
 */
Config::define('WP_DEBUG_LOG', env('WP_DEBUG_LOG') ?? true);
