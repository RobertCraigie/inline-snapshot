from inline_snapshot import snapshot


def test_help_message(testdir):
    result = testdir.runpytest_subprocess("--help")
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["inline-snapshot:", "*--inline-snapshot*"])


def test_create(project):
    project.setup(
        """\
def test_a():
    assert 5==snapshot()
"""
    )

    result = project.run()

    result.assert_outcomes(errors=1, passed=1)

    assert result.report == snapshot(
        "Error: 1 snapshots are missing values (--inline-snapshot=create)"
    )

    result = project.run("--inline-snapshot=create")

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("defined values for 1 snapshots")

    assert project.source == snapshot(
        """\
def test_a():
    assert 5==snapshot(5)
"""
    )


def test_fix(project):
    project.setup(
        """\
def test_a():
    assert 5==snapshot(4)
"""
    )

    result = project.run()

    result.assert_outcomes(failed=1)

    assert result.report == snapshot(
        "Error: 1 snapshots have incorrect values (--inline-snapshot=fix)"
    )

    result = project.run("--inline-snapshot=fix")

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("fixed 1 snapshots")

    assert project.source == snapshot(
        """\
def test_a():
    assert 5==snapshot(5)
"""
    )


def test_update(project):
    project.setup(
        """\
def test_a():
    assert "5" == snapshot('''5''')
"""
    )

    result = project.run()

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("")

    result = project.run("--inline-snapshot=update")

    assert result.report == snapshot("updated 1 snapshots")

    assert project.source == snapshot(
        """\
def test_a():
    assert "5" == snapshot("5")
"""
    )


def test_trim(project):
    project.setup(
        """\
def test_a():
    assert 5 in snapshot([4,5])
"""
    )

    result = project.run()

    result.assert_outcomes(passed=1)

    assert result.report == snapshot(
        "Info: 1 snapshots can be trimmed (--inline-snapshot=trim)"
    )

    result = project.run("--inline-snapshot=trim")

    assert result.report == snapshot("trimmed 1 snapshots")

    assert project.source == snapshot(
        """\
def test_a():
    assert 5 in snapshot([5])
"""
    )


def test_multiple(project):
    project.setup(
        """\
def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(8)
    assert 5 == snapshot(4)
"""
    )

    result = project.run()

    result.assert_outcomes(failed=1)

    assert result.report == snapshot(
        """
Error: 1 snapshots have incorrect values (--inline-snapshot=fix)
Info: 1 snapshots can be trimmed (--inline-snapshot=trim)
"""
    )

    result = project.run("--inline-snapshot=trim,fix")

    assert result.report == snapshot(
        """
Info: 1 snapshots changed their representation (--inline-snapshot=update)
fixed 1 snapshots
trimmed 1 snapshots
updated 1 snapshots
"""
    )

    assert project.source == snapshot(
        """\
def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(5)
    assert 5 == snapshot(5)
"""
    )


def test_deprecated_option(project):
    project.setup(
        """\
def test_a():
    pass
"""
    )

    result = project.run("--update-snapshots=failing")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=failing is deprecated, please use --inline-snapshot=fix"
    )

    result = project.run("--update-snapshots=new")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=new is deprecated, please use --inline-snapshot=create"
    )

    result = project.run("--update-snapshots=all")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=all is deprecated, please use --inline-snapshot=create,fix"
    )

    result = project.run("--inline-snapshot-disable", "--inline-snapshot=fix")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --inline-snapshot-disable can not be combined with other flags (fix)"
    )

    result = project.run("--update-snapshots=failing", "--inline-snapshot=fix")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=failing is deprecated, please use only --inline-snapshot"
    )


def test_black_config(project):
    project.setup(
        """\
def test_a():
    assert list(range(10)) == snapshot([])
"""
    )

    project.format()

    assert project.is_formatted()

    project.pyproject(
        """
[tool.black]
line-length=50
"""
    )

    assert project.is_formatted()

    project.run("--inline-snapshot=fix")

    assert project.source == snapshot(
        """\
def test_a():
    assert list(range(10)) == snapshot(
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )
"""
    )

    assert project.is_formatted()


def test_disabled(project):
    project.setup(
        """\
def test_a():
    assert 4==snapshot(5)
"""
    )

    result = project.run("--inline-snapshot-disable")
    result.assert_outcomes(failed=1)

    result = project.run("--inline-snapshot=fix")
    assert project.source == snapshot(
        """\
def test_a():
    assert 4==snapshot(4)
"""
    )

    result = project.run("--inline-snapshot-disable")
    result.assert_outcomes(passed=1)


def test_compare(project):
    project.setup(
        """\
def test_a():
    assert "a"==snapshot("b")
"""
    )

    result = project.run()
    assert result.errorLines() == snapshot(
        """
>       assert "a"==snapshot("b")
E       AssertionError: assert 'a' == 'b'
E         - b
E         + a
"""
    )

    project.setup(
        """\
def test_a():
    assert snapshot("b")=="a"
"""
    )

    result = project.run()
    assert result.errorLines() == snapshot(
        """
>       assert snapshot("b")=="a"
E       AssertionError: assert 'b' == 'a'
E         - a
E         + b
"""
    )


def test_assertion_error_loop(project):
    project.setup(
        """\
for e in (1, 2):
    assert e == snapshot()
"""
    )
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot()
"""
    )


def test_assertion_error_multiple(project):
    project.setup(
        """\
for e in (1, 2):
    assert e == snapshot(1)
"""
    )
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
    )


def test_assertion_error(project):
    project.setup("assert 2 == snapshot(1)")
    assert repr(snapshot) == "snapshot"
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
    )


def test_run_without_pytest(pytester):
    # snapshots are deactivated by default
    pytester.makepyfile(
        test_file="""
from inline_snapshot import snapshot
s=snapshot([1,2])
assert isinstance(s,list)
assert s==[1,2]
"""
    )

    result = pytester.runpython("test_file.py")

    assert result.ret == 0
