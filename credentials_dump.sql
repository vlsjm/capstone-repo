-- Credentials-only PostgreSQL data dump for Resource Hive
-- Contains only the requested access accounts and their profile access settings.

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
1	pbkdf2_sha256$1000000$CddNQ5oFrwFF1EjWsWYtkW$XNiGALDVbrOqDk5PEysxPn5ny/UVY4u8c5zaE3G9h1E=	\N	t	ADMIN				t	t	2026-06-27 00:00:00+00
2	pbkdf2_sha256$1000000$oA55rPxOBQr8zmlbE4VwLT$6VH4nECFN+0SBGQ1XYNFwI/5NczVPE+PmS9V/JkBtSc=	\N	f	USER				f	t	2026-06-27 00:00:00+00
\.

COPY public.app_userprofile (id, role, department_id, phone, user_id, designation, auto_enable_at, must_change_password, has_limited_access) FROM stdin;
1	ADMIN	\N	\N	1	\N	\N	f	f
2	USER	\N	\N	2	\N	\N	f	f
\.