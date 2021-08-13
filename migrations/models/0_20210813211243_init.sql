-- upgrade --
CREATE TABLE IF NOT EXISTS "problem_groups" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "scope" VARCHAR(255) NOT NULL,
    "uname" VARCHAR(255) NOT NULL,
    "mail" VARCHAR(255) NOT NULL,
    "uname_lower" VARCHAR(255) NOT NULL,
    "mail_lower" VARCHAR(255) NOT NULL,
    "gravatar" VARCHAR(255) NOT NULL,
    "student_id" VARCHAR(255) NOT NULL  DEFAULT '',
    "real_name" VARCHAR(255) NOT NULL  DEFAULT '',
    "salt" VARCHAR(255) NOT NULL  DEFAULT '',
    "hash" VARCHAR(255) NOT NULL  DEFAULT '',
    "role" VARCHAR(255) NOT NULL  DEFAULT 'user',
    "register_ip" VARCHAR(255) NOT NULL  DEFAULT '0.0.0.0',
    "login_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "login_ip" VARCHAR(255) NOT NULL  DEFAULT '0.0.0.0',
    CONSTRAINT "uid_users_scope_848d1c" UNIQUE ("scope", "uname_lower"),
    CONSTRAINT "uid_users_scope_0b2d4d" UNIQUE ("scope", "mail_lower")
);
CREATE TABLE IF NOT EXISTS "domains" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "url" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "gravatar" VARCHAR(255) NOT NULL  DEFAULT '',
    "bulletin" TEXT NOT NULL,
    "owner_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_domains_name_fe38ea" ON "domains" ("name");
CREATE INDEX IF NOT EXISTS "idx_domains_owner_i_93ac63" ON "domains" ("owner_id");
CREATE TABLE IF NOT EXISTS "domain_invitations" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "code" VARCHAR(255) NOT NULL,
    "role" VARCHAR(255) NOT NULL,
    "expire_at" TIMESTAMPTZ NOT NULL,
    "domain_id" UUID NOT NULL REFERENCES "domains" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_domain_invi_domain__f2bef7" UNIQUE ("domain_id", "code")
);
CREATE INDEX IF NOT EXISTS "idx_domain_invi_code_9286f5" ON "domain_invitations" ("code");
CREATE INDEX IF NOT EXISTS "idx_domain_invi_domain__f66b61" ON "domain_invitations" ("domain_id");
CREATE TABLE IF NOT EXISTS "domain_roles" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "role" VARCHAR(255) NOT NULL,
    "permission" JSONB NOT NULL,
    "domain_id" UUID NOT NULL REFERENCES "domains" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_domain_role_domain__8fe567" UNIQUE ("domain_id", "role")
);
CREATE INDEX IF NOT EXISTS "idx_domain_role_domain__5445d1" ON "domain_roles" ("domain_id");
CREATE TABLE IF NOT EXISTS "domain_users" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "role" VARCHAR(255) NOT NULL,
    "domain_id" UUID NOT NULL REFERENCES "domains" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_domain_user_domain__13641a" UNIQUE ("domain_id", "user_id")
);
CREATE INDEX IF NOT EXISTS "idx_domain_user_domain__0050a2" ON "domain_users" ("domain_id");
CREATE INDEX IF NOT EXISTS "idx_domain_user_user_id_88ba49" ON "domain_users" ("user_id");
CREATE TABLE IF NOT EXISTS "problems" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "url" VARCHAR(255) NOT NULL UNIQUE,
    "title" VARCHAR(255) NOT NULL,
    "content" VARCHAR(255) NOT NULL  DEFAULT '',
    "hidden" BOOL NOT NULL  DEFAULT False,
    "num_submit" INT NOT NULL  DEFAULT 0,
    "num_accept" INT NOT NULL  DEFAULT 0,
    "data_version" INT NOT NULL  DEFAULT 2,
    "languages" TEXT NOT NULL,
    "domain_id" UUID NOT NULL REFERENCES "domains" ("id") ON DELETE CASCADE,
    "owner_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT,
    "problem_group_id" UUID NOT NULL REFERENCES "problem_groups" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_problems_domain__4f4ac8" ON "problems" ("domain_id");
CREATE INDEX IF NOT EXISTS "idx_problems_owner_i_6b73d0" ON "problems" ("owner_id");
CREATE INDEX IF NOT EXISTS "idx_problems_problem_26c817" ON "problems" ("problem_group_id");
CREATE TABLE IF NOT EXISTS "problem_sets" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "url" VARCHAR(255) NOT NULL UNIQUE,
    "title" VARCHAR(255) NOT NULL,
    "content" VARCHAR(255) NOT NULL  DEFAULT '',
    "hidden" BOOL NOT NULL  DEFAULT False,
    "scoreboard_hidden" BOOL NOT NULL  DEFAULT False,
    "available_time" TIMESTAMPTZ NOT NULL,
    "due_time" TIMESTAMPTZ NOT NULL,
    "num_submit" INT NOT NULL  DEFAULT 0,
    "num_accept" INT NOT NULL  DEFAULT 0,
    "domain_id" UUID NOT NULL REFERENCES "domains" ("id") ON DELETE CASCADE,
    "owner_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_problem_set_domain__cc836a" ON "problem_sets" ("domain_id");
CREATE INDEX IF NOT EXISTS "idx_problem_set_owner_i_dd413a" ON "problem_sets" ("owner_id");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(20) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "problem_set_problems" (
    "problem_sets_id" UUID NOT NULL REFERENCES "problem_sets" ("id") ON DELETE CASCADE,
    "problem_id" UUID NOT NULL REFERENCES "problems" ("id") ON DELETE CASCADE
);
