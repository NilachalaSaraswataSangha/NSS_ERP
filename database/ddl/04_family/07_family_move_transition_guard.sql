-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 07_family_move_transition_guard.sql
-- Object: nss.fn_family_move_requires_transition() +
--         constraint trigger on nss.family_relationship
-- Depth: 4 (depends on family_relationship,
--            family_transition_history)
-- Version: 1.0
-- Authority: SOL-FAM-005 §10–§12, FAM-011..FAM-016
-- Owner: NSS_ERP_ADMIN
--
-- Purpose:
--   Backstop invariant — when a person is MOVED from one
--   family to another, the move must be recorded in
--   family_transition_history. This closes at the database
--   level the class of bug that database/fixes/
--   fix_missing_ghost_transitions.sql had to repair by hand:
--   a person whose old family_relationship was closed but
--   whose transition was never recorded, leaving them an
--   invisible "ghost" in the family graph.
--
-- What counts as a MOVE (enforced):
--   A family_relationship row transitions is_current TRUE→FALSE
--   AND, at end of transaction, the same person is a current
--   member of a DIFFERENT family. That is the definition of a
--   move — they left one family and landed in another.
--
-- What is NOT a move (deliberately allowed, no transition):
--   A plain removal / death / correction — the person's row is
--   closed and they end up in NO other current family. The
--   Remove Member flow (api/routers/family.py) does exactly
--   this and legitimately writes no transition record.
--
-- Why a DEFERRABLE INITIALLY DEFERRED constraint trigger:
--   In both move paths the application closes the old
--   relationship BEFORE it inserts the transition row (and,
--   for Add Member, before it inserts the new-family
--   relationship). A non-deferred trigger would fire too early
--   and see neither. Deferring to COMMIT lets the whole move
--   settle first, then verifies the invariant holds.
--
-- Assumption:
--   A person is current in at most one family at a time (the
--   app collapses all other current memberships on any move).
--   "Current in a different family after a close" is therefore
--   an unambiguous move signal.
--
-- No migration/fix script: this ships as DDL, re-runnable via
-- the standard build (DROP ... IF EXISTS makes it idempotent).
-- =====================================================

CREATE OR REPLACE FUNCTION nss.fn_family_move_requires_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_now_in_other_family BOOLEAN;
    v_has_transition      BOOLEAN;
BEGIN
    -- Did the person end up a current member of a DIFFERENT family?
    -- If not, this close is a removal/death/correction, not a move —
    -- no transition record is required, so allow it.
    SELECT EXISTS (
        SELECT 1
        FROM nss.family_relationship fr
        WHERE fr.person_pk = NEW.person_pk
          AND fr.is_current = TRUE
          AND fr.family_group_pk <> NEW.family_group_pk
    ) INTO v_now_in_other_family;

    IF NOT v_now_in_other_family THEN
        RETURN NULL;
    END IF;

    -- It IS a move: a transition record for leaving THIS family
    -- must exist by the end of the transaction.
    SELECT EXISTS (
        SELECT 1
        FROM nss.family_transition_history fth
        WHERE fth.person_pk = NEW.person_pk
          AND fth.old_family_group_pk = NEW.family_group_pk
    ) INTO v_has_transition;

    IF NOT v_has_transition THEN
        RAISE EXCEPTION
            'Family move guard: person % left family % (now current in another family) with no family_transition_history record. A move between families must record the transition in the same transaction.',
            NEW.person_pk, NEW.family_group_pk
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NULL;
END;
$$;

-- Idempotent: constraint triggers support neither OR REPLACE
-- nor IF NOT EXISTS, so drop-then-create.
DROP TRIGGER IF EXISTS trg_family_move_requires_transition
    ON nss.family_relationship;

CREATE CONSTRAINT TRIGGER trg_family_move_requires_transition
    AFTER UPDATE ON nss.family_relationship
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    WHEN (OLD.is_current = TRUE AND NEW.is_current = FALSE)
    EXECUTE FUNCTION nss.fn_family_move_requires_transition();
