from src.lifecycle import can_transition, next_action, normalize_status


def test_normalize_legacy_pending_to_saved():
    assert normalize_status(None) == 'saved'
    assert normalize_status('pending') == 'saved'


def test_core_lifecycle_transitions():
    assert can_transition('saved', 'ready')
    assert can_transition('ready', 'applied')
    assert can_transition('applied', 'interview')
    assert can_transition('interview', 'offer')
    assert can_transition('offer', 'negotiation')
    assert can_transition('negotiation', 'accepted')
    assert not can_transition('applied', 'offer')
    assert not can_transition('offer', 'accepted')


def test_next_action_for_offer_and_negotiation():
    assert next_action('offer').key == 'negotiate'
    action = next_action('negotiation')
    assert action.key == 'accept_offer'
    assert action.requires_confirmation is True


def test_applied_prioritizes_reply_then_followup_then_outreach():
    assert next_action('applied', has_reply=True).key == 'respond'
    assert next_action('applied', followup_due=True).key == 'followup'
    assert next_action('applied', has_contacts=True, has_outreach=False).key == 'outreach'
    assert next_action('applied', has_contacts=True, has_outreach=True).key == 'interview_prep'

def test_terminal_actions_are_safe():
    assert next_action('accepted').key == 'complete'
    assert next_action('rejected').key == 'complete'
