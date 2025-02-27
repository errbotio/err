v9.9.9 (unreleased)
-------------------

fixes:

- docs: add unreleased section (#1681)
- fix: check only activate plugins listed in CORE_PLUGINS (#1601)
- chore: bump jinja to 3.1.3 (#1684)
- chore: bump actions/setup-python version (#1686, #1700)
- chore: bump actions/checkout version (#1696, #1704)
- chore: optimize Dockerfile (#1679)
- docs: fix telegram install command (#1697)
- chore: add python versions to test (#1705)
- chore: remove python 3.8 support (#1707)
- chore: use ruff for formatting (#1706)
- chore: bump setuptools to 75.7.0 (#1709)
- chore: bump pyOpenSSL to 24.3.0 (#1710)
- Fix: situationally broken apropos command (#1711)


v6.2.0 (2024-01-01)
-------------------

breaking:

- backend/slack: remove slack and slack_rtm built-in backends (#1581)
- core/logging: deprecate SENTRY_TRANSPORT config (#1604)
- core: removing py37 support (#1652)

features:

- core/plugins: detect plugins using entrypoints (#1590)
- core/logging: add new SENTRY_OPTIONS config (#1597)
- core/plugins: make slack, mattermost and discord backends available as install requirements (#1611)

fixes:

- docs: add unreleased section (#1576)
- docs: update broken URL for Markdown Extra (#1572)
- chore: bump actions/setup-python version (#1575, #1593, #1609, #1626, #1642, #1650, #1659, #1674)
- backend/telegram: fix missing imports (#1574)
- chore: ci improvements (#1577, #1583)
- chore: add docs build to ci (#1582)
- backend/xmpp: fix forward type references (#1578)
- chore: remove campfire references (#1584)
- chore/setup: fix exception when installing on python <3.7 (#1585)
- docs: typos (#1589, #1594)
- chore: simplify isort config using black (#1595)
- fix: detecting entrypoint module paths (#1603)
- chore: fix Docker build to use local tree (#1608)
- chore: bump actions/checkout version (#1610, #1625, #1637, #1644, #1653, #1656, #1658, #1663)
- docs: link to external Discord plugin documentation (#1615)
- chore: add ARG to Dockerfile and add proper stop signal (#1613)
- fix: update module versions and build (#1627)
- chore: update setuptools version (#1628)
- refactor: detecting entry point plugins (#1630)
- chore: bump mr-smithers-excellent/docker-build-push version (#1633)
- docs: fix example code in the testing section (#1643)
- chore: update all core dependencies (#1651)
- fix: use template file for webserver plugin echo output (#1654)
- chore: update repos.json (#1660)
- docs: add readthedocs yaml config (#1661)
- fix: broken integration tests (#1668)
- style: replace format() with f-strings (#1667)
- migrate from external mock package to stdlib unittest.mock (#1673)
- fix: import of Mapping from collections.abc (#1675)
- backend: update irc, telegram and xmpp dependencies (#1655)


v6.1.9 (2022-06-11)
-------------------

features:

- core: set default backend to Text (#1522)
- core: option to divert all commands to private or thread (#1528)
- core: add type hints to core and backend functions (#1542)
- docs: add ACL and numerous backends to official documentation (#1552)
- core: add Python 3.10 to automated tests (#1539)
- core: add room acl attribute (#1530)
- chore: refactor Dockerfile errbot install and python version bump (#1571)

fixes:

- core: success handling for update_repos (#1520)
- core/plugins: cascade dependency plugins (#1519)
- core/plugins: reload all repo plugins when updating a repo (#1521)
- plugin_manager: correct syntax error (#1524)
- backend/text: add stub send_stream_request method (#1527)
- backend/hipchat: remove HipChat backend (#1525)
- backend/test: shutdown sequence to address test failure (#1535)
- core: various minor logging improvements (#1536)
- chore: various minor formatting improvements (#1541)
- docs: update spark plugin reference (#1546)
- fix: python 2 version references in docs and init template (#1543)
- backends: deprecate built-in Slack and SlackRTM (#1526)
- chore: remove python 3.6 checks and test environment (#1540)
- chore: add/update issue templates (#1554)
- chore: pin all package dependencies (#1553, #1559)
- core/webserver: use errbot loglevel for consistent logging. (#1556)
- fix/core: prevent infinite loop when only BOT_PREFIX is passed (#1557)
- chore: bump actions/setup-python from 2 to 3.1.0 (#1563)
- chore: Set permissions for GitHub actions (#1565)
- fix: removed deprecated argument reconnection_interval for irc v20.0 (#1568)
- docs: Add Gentoo packages (#1567)
- chore: bump actions/setup-python from 3.1.0 to 3.1.2 (#1564)
- fix: circular dependencies error when there are none (#1505)

v6.1.8 (2021-06-21)
-------------------

features:

- core/plugin: method to append argparse options to Command object (#1394)
- backends: Add identifier for room join and room leave callbacks (#1500)
- backends/test: allow attachments to pytest messages as extras (#1489)
- core/acl: Add allowargs / denyargs filters to ACL (#1509)
- core/bootstrap: Small logging fixes to BOT_LOG_FILE and FORMATTER (#1513)
- core/plugin: Support room names with spaces (#1262)

fixes:

- core/cli: failure when passing relative directory during --init (#1511)
- backend/xmpp: include message delayed for send/received messages (#1270)
- backend/xmpp: "unexpected keyword argument 'wait'" when connecting (#1507)
- docs: update broken readme link to plugin development docs (#1504)
- close threadpool on exit (#1486)
- docs: remove matrix link (#1502)
- docs: Update backend screenshots (#1499)
- docs: Remove Google+ references (#1497)
- core: Split messages using `split()` instead of whitespace (#1496)
- chore/plugin: whoami formatting (#1459)
- backend/GUI: Remove GUI backend (#1495)

v6.1.7 (2020-12-18)
-------------------

features:

- core: Add support for python3.9 (#1477)
- chore: Allow dependabot to check GitHub actions weekly (#1464)
- chore: Add Dockerfile (#1482)

fixes:

- core: AttributeError on Blacklisted plugins (#1369)
- chore: Remove travis configuration (#1478)
- chore: minor code cleanup (#1465)
- chore: Use black codestyle (#1457, #1485)
- chore: Use twine to check dist (#1485)
- chore: remove codeclimate and eslint configs (#1490)

v6.1.6 (2020-11-16)
-------------------

features:

- core: Update code to support markdown 3 (#1473)

fixes:

- backends: Set email property as non-abstract (#1461)
- SlackRTM: username to userid method signature (#1458)
- backends: AttributeError in callback_reaction (#1467)
- docs: webhook examples (#1471)
- cli: merging configs with unknown keys (#1470)
- plugins: Fix error when plugin plug file is missing description (#1462)
- docs: typographical issues in setup guide (#1475)
- refactor: Split changelog by major versions (#1474)

v6.1.5 (2020-10-10)
-------------------

features:

-  XMPP: Replace sleekxmpp with slixmpp (#1430)
-  New callback for reaction events (#1292)
-  Added email property foriPerson object on all backends (#1186, #1456)
-  chore: Add github actions (#1455)

fixes:

-  Slack: Deprecated method calls (#1432, #1438)
-  Slack: Increase message size limit. (#1333)
-  docs: Remove Matrix backend link (#1445)
-  SlackRTM: Missing 'id\_' in argument (#1443)
-  docs: fixed rendering with double hyphens (#1452)
-  cli: merging configs via ``--storage-merge`` option (#1450)

v6.1.4 (2020-05-15)
-------------------

fixes:

-  403 error when fetching plugin repos index (#1425)

v6.1.3 (2020-04-19)
-------------------

features:

-  Add security linter (#1314)
-  Serve version.json on errbot.io and update version checker plugin (#1400)
-  Serve repos.json on errbot.io (#1403, #1406)
-  Include SlackRTM backend (beta) (#1416)

fixes:

-  Make plugin name clashes deterministic (#1282)
-  Fix error with Flows missing descriptions (#1405)
-  Fix ``!repos update`` object attribute error (#1410)
-  Fix updating remove repos using ``!repos update`` (#1413)
-  Fix deprecation warning (#1423)
-  Varios documentation fixes (#1404, #1411, #1415)

v6.1.2 (2019-12-15)
-------------------

fixes:

-  Add ability to re-run –init safely (#1390)
-  fix #1375 by managing errors on lack of version endpoint.
-  Fixed a deprecation warning for 3.9 on Mapping.
-  removing the intermediate domain requiring a certificate.
-  Fix package name for sentry-sdk flask integration
-  Add support to sentry FlaskIntegration
-  Migrate from raven (deprecated) to new sentry-sdk
-  fix: Log errors when present
-  Make chatroom log more descriptive
-  Set admin check log as debug
-  Add admin warnings to log
-  Fix: Advanced loop graph does not reflect the image
-  make the TestBot start timeout parameterized
-  errbot/plugin_manager: only check for /proc/1/cgroup if path exists to fix warning
-  removed (c) Apple asset we completely missed.
-  fix double threading in slack backend if DIVERT_TO_THREAD is used
-  pop up the timeout for travis
-  Makes the timeout feedback better on tests. (#1366)
-  Move all tox environments to use py37 (#1342)
-  Remove empty "text" body on Slack send_card (#1336)
-  Load class source in reloading plugins (#1347)
-  test: Rename assertCommand -> assertInCommand (#1351)
-  Enforce BOT_EXTRA_BACKEND_DIR is a list type. (#1358)
-  Fix #1360 Cast pathlib.Path objects to strings for use with sys.path
   (#1361)

v6.1.1 (2019-06-22)
-------------------

fixes:

-  Installation using wheel distribution on python 3.6 or older

v6.1.0 (2019-06-16)
-------------------

features:

-  Use python git instead of system git binary (#1296)

fixes:

-  ``errbot -l`` cli error (#1315)
-  Slack backend by pinning slackclient to supported version (#1343)
-  Make –storage-merge merge configs (#1311)
-  Exporting values in backup command (#1328)
-  Rename Spark to Webex Teams (#1323)
-  Various documentation fixes (#1310, #1327, #1331)

v6.0.0 (2019-03-23)
-------------------

features:

-  TestBot: Implement inject_mocks method (#1235)
-  TestBot: Add multi-line command test support (#1238)
-  Added optional room arg to inroom
-  Adds ability to go back to a previous room
-  Pass telegram message id to the callback

fixes:

-  Remove extra spaces in uptime output
-  Fix/backend import error messages (#1248)
-  Add docker support for installing package dependencies (#1245)
-  variable name typo (#1244)
-  Fix invalid variable name (#1241)
-  sanitize comma quotation marks too (#1236)
-  Fix missing string formatting in "Command not found" output (#1259)
-  Fix webhook test to not call fixture directly
-  fix: arg_botcmd decorator now can be used as plain method
-  setup: removing dnspython
-  pin markdown <3.0 because safe is deprecated

v6.0.0-alpha (2018-06-10)
-------------------------

major refactoring:

-  Removed Yapsy dependency
-  Replaced back Bottle and Rocket by Flask
-  new Pep8 compliance
-  added Python 3.7 support
-  removed Python 3.5 support
-  removed old compatibility cruft
-  ported formats and % str ops to f-strings
-  Started to add field types to improve type visibility across the codebase
-  removed cross dependencies between PluginManager & RepoManager

fixes:

-  Use sys.executable explicitly instead of just 'pip' (thx Bruno Oliveira)
-  Pycodestyle fixes (thx Nitanshu)
-  Help: don't add bot prefix to non-prefixed re cmds (#1199) (thx Robin Gloster)
-  split_string_after: fix empty string handling (thx Robin Gloster)
-  Escaping bug in dynamic plugins
-  botmatch is now visible from the errbot module (fp to Guillaume Binet)
-  flows: hint boolean was not forwarded
-  Fix possible event without bot_id (#1073) (thx Roi Dayan)
-  decorators were working only if kwargs were empty
-  Message.clone was ignoring partial and flows

features:

-  partial boolean to flag partial mesages (thx Meet Mangukiya)
-  Slack: room joined callback (thx Jeremy Kenyon)
-  XMPP: real_jid to get the jid the users logged in (thx Robin Gloster)
-  The callback order set in the config is not globally respected
-  Added a default parameter to the storage context manager

.. v9.9.9 (leave that there so master doesn't complain)
