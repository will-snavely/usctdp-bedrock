<?php
/**
 * Emergency mitigation for the 2026-08-01 incident (rogue Administrator
 * accounts created as wp2_*@wp2shell.invalid). The exploit chain relies on
 * nested WordPress REST API batch requests (WP_REST_Server::serve_batch_
 * request_v1(), core since WP 5.6) to reach Customizer changeset /
 * nav_menu_item code paths that a single ordinary request can't touch.
 * This site has no legitimate use for batch requests, so disabling the
 * endpoint outright closes that path without first needing to pin down
 * every step of the chain.
 *
 * rest_pre_dispatch fires on every WP_REST_Server::dispatch() call,
 * including each nested sub-request inside a batch - so this also blocks
 * batch-within-batch attempts, not just the outer request.
 */
add_filter('rest_pre_dispatch', function ($result, $server, $request) {
    if (preg_match('#^/batch/#', $request->get_route())) {
        return new WP_Error(
            'rest_batch_disabled',
            __('Batch requests are disabled on this site.', 'usctdp'),
            ['status' => 403]
        );
    }
    return $result;
}, 10, 3);
