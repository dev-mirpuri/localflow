from localflow_engine.hotkey import Hotkey

CTRL = ("right ctrl", 29)
ESC = ("esc", 1)
A = ("a", 30)


def press(hotkey: Hotkey, key: tuple[str, int], now: float, **flags: bool):
    return hotkey.key(*key, True, now, **flags)


def release(hotkey: Hotkey, key: tuple[str, int], now: float, **flags: bool):
    return hotkey.key(*key, False, now, **flags)


def test_hotkey_down_starts_recording_at_once():
    assert press(Hotkey("right ctrl"), CTRL, 0) == (["start"], False)


def test_release_at_250_ms_or_later_finishes():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    assert release(hotkey, CTRL, 10.25) == (["finish"], False)


def test_release_before_250_ms_waits_for_a_second_tap_then_discards_after_350_ms():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    assert release(hotkey, CTRL, 10.249) == ([], False)
    assert hotkey.tick(10.598) == []
    assert hotkey.tick(10.6) == ["discard"]
    assert hotkey.tick(11) == []


def double_tap(hotkey: Hotkey) -> None:
    """Leaves the Hotkey in Hands-free at t=10.2, with the key up."""
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    assert press(hotkey, CTRL, 10.15) == (["hands_free"], False)
    assert release(hotkey, CTRL, 10.2) == ([], False)


def test_second_press_within_350_ms_of_the_release_goes_hands_free():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    assert press(hotkey, CTRL, 10.399) == (["hands_free"], False)
    assert hotkey.tick(20) == []


def test_hands_free_ignores_the_second_release_and_finishes_on_the_next_press():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert hotkey.tick(15) == []
    assert press(hotkey, CTRL, 15) == (["finish"], False)
    assert release(hotkey, CTRL, 15.1) == ([], False)


def test_presses_during_processing_are_ignored_and_their_key_up_does_nothing():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 11)
    assert press(hotkey, CTRL, 11.5) == ([], False)
    assert release(hotkey, CTRL, 11.6) == ([], False)
    assert press(hotkey, CTRL, 12) == ([], False)
    hotkey.done()
    assert release(hotkey, CTRL, 13) == ([], False)
    assert hotkey.tick(20) == []
    assert press(hotkey, CTRL, 20) == (["start"], False)


def test_auto_repeat_of_the_hotkey_is_ignored():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    press(hotkey, CTRL, 10.15)
    assert press(hotkey, CTRL, 10.65) == ([], False)
    assert press(hotkey, CTRL, 10.68) == ([], False)
    release(hotkey, CTRL, 11)
    assert press(hotkey, CTRL, 12) == (["finish"], False)
    hotkey.done()
    assert press(hotkey, CTRL, 12.6) == ([], False)
    release(hotkey, CTRL, 13)
    assert press(hotkey, CTRL, 14) == (["start"], False)


def test_other_keys_do_nothing_when_idle():
    hotkey = Hotkey("right ctrl")
    assert press(hotkey, A, 10) == ([], False)
    assert release(hotkey, A, 10.1) == ([], False)
    assert press(hotkey, ("left ctrl", 29), 11) == ([], False)


def test_other_key_down_while_holding_cancels_and_the_hotkey_release_does_nothing():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    assert press(hotkey, A, 10.5) == (["cancel"], False)
    assert release(hotkey, A, 10.6) == ([], False)
    assert release(hotkey, CTRL, 11) == ([], False)
    assert hotkey.tick(20) == []
    assert press(hotkey, CTRL, 20) == (["start"], False)


def test_other_keys_are_ignored_in_tap_wait():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    assert press(hotkey, A, 10.1) == ([], False)
    assert release(hotkey, A, 10.12) == ([], False)
    assert press(hotkey, CTRL, 10.15) == (["hands_free"], False)


def test_other_keys_are_ignored_in_hands_free():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert press(hotkey, A, 11) == ([], False)
    assert release(hotkey, A, 11.1) == ([], False)
    assert press(hotkey, CTRL, 12) == (["finish"], False)


def test_a_key_held_before_the_hotkey_does_not_cancel_by_repeating():
    hotkey = Hotkey("right ctrl")
    press(hotkey, A, 9)
    press(hotkey, CTRL, 10)
    assert press(hotkey, A, 10.5) == ([], False)
    assert release(hotkey, A, 10.6) == ([], False)
    assert release(hotkey, CTRL, 11) == (["finish"], False)


def test_esc_while_holding_cancels_and_is_swallowed_with_its_repeats_and_key_up():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    assert press(hotkey, ESC, 10.5) == (["cancel"], True)
    assert press(hotkey, ESC, 11) == ([], True)
    assert release(hotkey, ESC, 11.1) == ([], True)
    assert release(hotkey, CTRL, 11.2) == ([], False)
    assert press(hotkey, ESC, 12) == ([], False)
    assert release(hotkey, ESC, 12.1) == ([], False)


def test_esc_in_tap_wait_cancels_and_is_swallowed():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    assert press(hotkey, ESC, 10.1) == (["cancel"], True)
    assert release(hotkey, ESC, 10.2) == ([], True)
    assert hotkey.tick(11) == []


def test_esc_in_hands_free_cancels_and_is_swallowed():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert press(hotkey, ESC, 11) == (["cancel"], True)
    assert release(hotkey, ESC, 11.1) == ([], True)
    assert press(hotkey, CTRL, 12) == (["start"], False)


def test_esc_passes_through_while_processing():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 11)
    assert press(hotkey, ESC, 11.5) == ([], False)
    hotkey.done()
    assert release(hotkey, ESC, 11.6) == ([], False)


def test_esc_held_from_before_the_recording_is_not_swallowed_on_release():
    hotkey = Hotkey("right ctrl")
    press(hotkey, ESC, 9)
    press(hotkey, CTRL, 10)
    assert press(hotkey, ESC, 10.1) == ([], False)
    assert release(hotkey, ESC, 10.2) == ([], False)
    assert release(hotkey, CTRL, 11) == (["finish"], False)


def test_holding_finishes_at_3_minutes_and_the_late_key_up_does_nothing():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    assert hotkey.tick(189.9) == []
    assert hotkey.tick(190) == ["finish"]
    assert hotkey.tick(191) == []
    assert release(hotkey, CTRL, 200) == ([], False)
    hotkey.done()
    assert press(hotkey, CTRL, 201) == (["start"], False)


def test_hands_free_finishes_3_minutes_after_the_first_press():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert hotkey.tick(189.9) == []
    assert hotkey.tick(190) == ["finish"]
    assert press(hotkey, CTRL, 191) == ([], False)


def test_a_key_event_after_the_limit_but_before_a_tick_still_finishes():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert press(hotkey, A, 190.5) == (["finish"], False)
    assert press(hotkey, ESC, 191) == ([], False)


def test_a_press_after_the_gap_but_before_a_tick_discards_and_starts_afresh():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    release(hotkey, CTRL, 10.05)
    assert press(hotkey, CTRL, 10.401) == (["discard", "start"], False)
    assert release(hotkey, CTRL, 11) == (["finish"], False)


def test_check_and_cross_finish_and_cancel_hands_free():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    assert hotkey.finish(11) == ["finish"]
    assert hotkey.cancel(11.1) == []
    hotkey.done()
    double_tap(hotkey)
    assert hotkey.cancel(11) == ["cancel"]
    assert hotkey.finish(11.1) == []
    assert press(hotkey, CTRL, 12) == (["start"], False)


def test_check_and_cross_do_nothing_outside_hands_free():
    hotkey = Hotkey("right ctrl")
    assert hotkey.finish(1) == []
    press(hotkey, CTRL, 10)
    assert hotkey.cancel(10.1) == []
    assert hotkey.finish(10.1) == []
    assert release(hotkey, CTRL, 11) == (["finish"], False)


def test_the_engines_own_ctrl_v_is_not_another_key():
    hotkey = Hotkey("right ctrl")
    press(hotkey, CTRL, 10)
    for event in (press, release):
        for key in (("ctrl", 29), ("v", 47)):
            assert event(hotkey, key, 10.1, injected=True) == ([], False)
    assert release(hotkey, CTRL, 11) == (["finish"], False)


def test_the_engines_own_ctrl_is_not_the_hotkey():
    hotkey = Hotkey("ctrl")
    assert press(hotkey, ("ctrl", 29), 10, injected=True) == ([], False)
    assert release(hotkey, ("ctrl", 29), 10.01, injected=True) == ([], False)
    assert hotkey.tick(20) == []


def test_a_real_key_up_flagged_by_mistake_does_not_leave_the_key_held():
    hotkey = Hotkey("right ctrl")
    press(hotkey, A, 9)
    release(hotkey, A, 9.1, injected=True)
    press(hotkey, CTRL, 10)
    assert press(hotkey, A, 10.5) == (["cancel"], False)


def test_a_swallowed_esc_whose_key_up_is_flagged_is_not_swallowed_again():
    hotkey = Hotkey("right ctrl")
    double_tap(hotkey)
    press(hotkey, ESC, 11)
    release(hotkey, ESC, 11.1, injected=True)
    assert press(hotkey, ESC, 12) == ([], False)
