-- =====================================================
-- NSS ERP
-- Module: Foundation / Audit
-- File: 15_audit_trigger.sql
-- Purpose: Database-level audit trigger that fires on
--          EVERY INSERT, UPDATE, DELETE across all nss
--          business tables. Writes to system_event_log
--          automatically — no application code can bypass.
-- Version: 1.0
-- Authority: SOL-AUDIT-004
-- Owner: NSS_ERP_ADMIN
-- Depends: 14_system_event_log.sql
--
-- Actor resolution: the trigger reads session variables
--   nss.actor_sangha_sevi_pk
--   nss.actor_user_account_pk
-- set by the application at the start of each request.
-- If not set, actor columns are NULL (system/anon).
-- =====================================================

-- ── Trigger function ────────────────────────────────

CREATE OR REPLACE FUNCTION nss.fn_audit_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_action        VARCHAR(50);
    v_record_pk     UUID;
    v_old_data      JSONB := NULL;
    v_new_data      JSONB := NULL;
    v_changed       JSONB := NULL;
    v_actor_ss      UUID  := NULL;
    v_actor_ua      UUID  := NULL;
    v_pk_col        TEXT;
BEGIN
    -- ── Determine action ────────────────────────────
    IF TG_OP = 'INSERT' THEN
        v_action := 'CREATE';
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'DELETE';
    END IF;

    -- ── Resolve the PK column (convention: <table>_pk) ──
    v_pk_col := TG_TABLE_NAME || '_pk';

    -- ── Extract record PK ───────────────────────────
    IF TG_OP = 'DELETE' THEN
        EXECUTE format('SELECT ($1).%I::UUID', v_pk_col)
            INTO v_record_pk USING OLD;
    ELSE
        EXECUTE format('SELECT ($1).%I::UUID', v_pk_col)
            INTO v_record_pk USING NEW;
    END IF;

    -- ── Capture row data as JSONB ───────────────────
    IF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
    ELSIF TG_OP = 'INSERT' THEN
        v_new_data := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        -- Build a diff: only changed columns
        SELECT jsonb_object_agg(key, jsonb_build_object(
                   'old', v_old_data -> key,
                   'new', value
               ))
          INTO v_changed
          FROM jsonb_each(v_new_data)
         WHERE v_old_data -> key IS DISTINCT FROM value;
    END IF;

    -- ── Read actor from session variables ───────────
    BEGIN
        v_actor_ss := current_setting('nss.actor_sangha_sevi_pk', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_actor_ss := NULL;
    END;

    BEGIN
        v_actor_ua := current_setting('nss.actor_user_account_pk', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_actor_ua := NULL;
    END;

    -- ── Insert audit row ────────────────────────────
    INSERT INTO nss.system_event_log (
        action,
        table_name,
        record_pk,
        actor_sangha_sevi_pk,
        actor_user_account_pk,
        module,
        summary,
        detail
    ) VALUES (
        v_action,
        TG_TABLE_NAME,
        v_record_pk,
        v_actor_ss,
        v_actor_ua,
        'trigger',
        v_action || ' on ' || TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'INSERT' THEN jsonb_build_object('new', v_new_data)
            WHEN TG_OP = 'DELETE' THEN jsonb_build_object('old', v_old_data)
            WHEN TG_OP = 'UPDATE' THEN jsonb_build_object('changed', v_changed)
        END
    );

    -- Return the appropriate row
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$;


-- ── Attach trigger to ALL business tables ───────────
-- Excludes: system_event_log (self), field_change_log (audit infra)

DO $$
DECLARE
    t TEXT;
    trigger_name TEXT;
    excluded_tables TEXT[] := ARRAY[
        'system_event_log',
        'field_change_log'
    ];
BEGIN
    FOR t IN
        SELECT tablename
          FROM pg_tables
         WHERE schemaname = 'nss'
           AND tablename != ALL(excluded_tables)
         ORDER BY tablename
    LOOP
        trigger_name := 'trg_audit_' || t;

        -- Drop if exists (idempotent re-run)
        EXECUTE format(
            'DROP TRIGGER IF EXISTS %I ON nss.%I',
            trigger_name, t
        );

        -- Create AFTER trigger for INSERT, UPDATE, DELETE
        EXECUTE format(
            'CREATE TRIGGER %I '
            'AFTER INSERT OR UPDATE OR DELETE ON nss.%I '
            'FOR EACH ROW EXECUTE FUNCTION nss.fn_audit_trigger()',
            trigger_name, t
        );

        RAISE NOTICE 'Attached audit trigger to nss.%', t;
    END LOOP;
END;
$$;
