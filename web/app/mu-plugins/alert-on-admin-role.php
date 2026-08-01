<?php
/**
 * Immediate email alert whenever any account is granted the Administrator
 * role - whether by being created as one, or promoted to one. Added after
 * the 2026-08-01 incident, where the rogue accounts sat unnoticed until
 * someone happened to check the Users screen.
 *
 * set_user_role fires for both a brand-new account's initial role
 * (wp_insert_user() calls set_role() internally as part of creating the
 * user) and an existing account being promoted, so this single hook covers
 * both cases without needing separate handling for each.
 */
add_action('set_user_role', function ($user_id, $role, $old_roles) {
    if ($role !== 'administrator') {
        return;
    }

    $user = get_userdata($user_id);
    if (!$user) {
        return;
    }

    wp_mail(
        get_option('admin_email'),
        sprintf('[%s] New Administrator account: %s', get_bloginfo('name'), $user->user_login),
        sprintf(
            "A user was just granted the Administrator role.\n\n" .
            "Username: %s\nEmail: %s\nUser ID: %d\nPrevious role(s): %s\n\n" .
            "If you didn't do this, investigate immediately.",
            $user->user_login,
            $user->user_email,
            $user_id,
            $old_roles ? implode(', ', $old_roles) : '(new account)'
        )
    );
}, 10, 3);
