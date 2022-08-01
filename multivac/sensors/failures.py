failure_categories = [
    {
        'tag': 'git',
        'title': 'Git problems',
        'description': 'Git-related problem: inaccessible remotes, '
                       'broken repository, '
                       'revision not found and other such stuff.',
    },
    {
        'tag': 'network',
        'description': 'Network problems: distribution repository '
                       'inaccessible, bad SSL certificates, etc.',
    },
    {
        'tag': 'tests',
        'description': 'Tests failed',
    },
    {
        'tag': 'tarantool',
        'description': 'Internal Tarantool problem',
    }
]
failure_specs = [
    {
        'type': 'git_unsafe_error',
        're': [r'.*fatal: unsafe repository.*'],
        'description': '',
    },
    {
        'type': 'testrun_test_failed',
        're': [
            r'.*\* fail: \d+.*',
        ],
        'description': 'Typical test failure.',
    },
    {
        'type': 'integration_vshard_test_failed',
        're': [
            r'.*===== \d+ tests failed:.*',
        ],
        'description': 'Typical test failure.',
    },
    {
        'type': 'package_building_error',
        're': [
            r'.*make\[3\]: \*\*\* .*c.o] Error 1.*',
            r'.*make\[\d\]: \*\*\* read jobs pipe: Resource temporarily unavailable.*',
        ],
        'description': '',
    },
    {
        'type': 'luajit_error',
        're': [
            r'.*fatal error, exiting the event loop.*',
            r'.*PANIC: unprotected error.*',
        ],
        'description': '',
    },
    {
        'type': 'database_error',
        're': [r'.*tarantool.error.DatabaseError.*'],
        'description': '',
    },
    {
        'type': 'yum_repo_error',
        're': [r'.*- Status code: (404|503) for.*'],
        'description': '',
    },
    {
        'type': 'testrun_internal',
        're': [r'.*\[Internal test-run error].*'],
        'description': '',
    },
    {
        'type': 'luatest_failed',
        're': [
            r'.*Test failed!.*',
            r'.*Tests with errors:.*',
        ],
        'description': '',
    },
    {
        'type': 'testrun_test_hung',
        're': [r'.*Test hung!.*'],
        'description': 'Test had started but did not return results.',
    },

    {
        'type': 'curl_error',
        're': [r'.*curl: \(22\) The requested URL returned error:.*'],
        'description': 'Generic error when trying to fetch network resource with curl.',
    },
    {
        'type': 'integration_tests_failed',
        're': [
            r'.*Captured stderr:.*',
            r'.*mFailed tests:.*',
        ],
        'description': 'Tests failed in an integration workflow between tarantool '
                       'and one of its modules',
    },
    {
        'type': 'python_not_found',
        're': [r'.*python3.\d+: not found.*'],
        'description': '',
    },
    {
        'type': 'vshard_error',
        're': [r'.*E> Error.*'],
        'description': '',
    },
    {
        'type': 'jepsen_error',
        're': [r'.*make\[\d+]: \*\*\* \[.*run-jepsen] Error.*'],
        'description': '',
    },
    {
        'type': 'dir_not_empty',
        're': [r'.*rm: cannot remove \'.*\': Directory not empty.*'],
        'description': '',
    },
    {
        'type': 'git_repo_access_error',
        're': [r'.*fatal: unable to access \'https://github.com.*',
               r'.* fatal: the remote end hung up unexpectedly.*',
               ],
        'description': '',
    },
    {
        'type': 'dpkg_buildpackage_error',
        're': [r'.*dpkg-buildpackage: error: debian/rules build.*'],
        'description': '',
    },

    {
        'type': 'git_submodule_error',
        're': [r'.*fatal: Needed a single revision.*'],
        'description': '',
    },
    {
        'type': 'go_tarantool_error',
        're': [r'.*FAIL\s+github.com/tarantool/go-tarantool.*'],
        'description': '',
    },
    {
        'type': 'ctest_error',
        're': [r'.*The following tests FAILED:.*'],
        'description': '',
    },
    {
        'type': 'lto_error',
        're': [r'.*lto-wrapper: fatal error:.*'],
        'description': '',
    },
    {
        'type': 'checkpatch',
        're': [r'.*total: [1-9][\d+]* errors, \d+ lines checked.*'],
        'description': 'Checkpatch is a linter that checks commits have proper descriptions, '
                       'and code changes have changelogs and documentation drafts.',
    },
    {
        'type': 'telegram_bot_error',
        're': [r'.*SyntaxError: EOL while scanning string literal.*'],
        'description': 'Telegram bot failed to process commit message.',
    },
    {
        'type': 'dependency_autoreconf',
        're': [r'.*exec: autoreconf: not found.*'],
        'description': 'Dependency error: autoreconf not found.',
    },
    {
        'type': 'ssl_certificate_problem',
        # this was named 'hashicorp_error' before,
        # but it can happen with other sources just as well
        're': [r'.*curl: \(60\) SSL certificate problem:.*'],
        'description': '',
    },
    {
        'type': 'tap_test_failed',
        're': [r'.*failed subtest: \d+.*'],
        'description': 'Failure of a TAP test.',
    },
    {
        'type': 'could_not_find_readline',
        're': [r'.*Could NOT find Readline.*'],
        'description': '',
    },
    {
        'type': 'linker_error',
        're': [r'.*clang-14: error: linker.*'],
        'description': '',
    },
    {
        'type': 'docker_rate_limit',
        're': [r'.*Error response from daemon: toomanyrequests.*'],
        'description': '',
    },

    {
        'type': 'linker_command_failed',
        're': [r'.*error: linker command failed.*'],
        'description': '',
    },
    {
        'type': 'docker_hub_unreachable',
        're': [
            r'.*Error response from daemon: Head .* EOF.*',
            r'.*Error response from daemon: Head .* request canceled.*',
            r'.*error parsing HTTP 408 response body: invalid character.*'
        ],
        'description': '',
    },
    {
        'type': 'repo_certificate_expired',
        're': [r'.*Certificate verification failed: The certificate is NOT trusted.*'],
        'description': '',
    },
    {
        'type': 'ninja_build_error',
        're': [r'.*ninja: error: build.ninja:\d*: multiple rules generate.*']
    },
    {
        'type': 'coveralls_io_unreachable',
        're': [r'.*##\[error\]Bad response: 4\d\d.*'],
        'description': 'Failed to connect to coveralls.io.',
    },
    {
        'type': 'changelog_error',
        're': [r'.*Unable to parse.*changelogs.*'],
        'description': 'Error in changelog syntax'
    },
    {
        'type': 'yum_repo_certificate_error',
        're': [
            # r'.*Err:\d+ https*://.* InRelease.*',
            r'.*Cannot retrieve metalink for repository: .*',
        ],
        'description': 'https://stackoverflow.com/questions/26734777/',
    },
]
