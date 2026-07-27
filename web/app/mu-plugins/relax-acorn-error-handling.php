<?php
/**
 * Acorn (Roots\Acorn\Bootstrap\HandleExceptions, dev-only - gated on
 * WP_DEBUG) converts PHP warnings/notices into thrown ErrorExceptions.
 * Valuable for catching real bugs in first-party code (this theme,
 * usctdp-mgmt), but third-party WordPress plugins weren't written expecting
 * that strictness - a single undefined-variable notice anywhere in any
 * installed plugin turns into a full crash instead of the harmless log entry
 * it would be everywhere else. Exempt everything outside our own code
 * instead of patching every plugin bug that trips this.
 */
add_filter('acorn/throw_error_exception', function ($should_throw, $e) {
    if (str_contains($e->getFile(), '/web/app/plugins/')) {
        return false;
    }
    return $should_throw;
}, 10, 2);
