
CREATE TYPE "status" AS ENUM ('የተጠናቀቀ', 'በመጠበቅ','የተሰረዘ');
--CREATE TYPE "day_status" AS ENUM ('completed', 'active', 'canceled');


CREATE TABLE public.users (
	id serial4 NOT NULL,
	telegram_id int8 NOT NULL,
	"name" varchar(100) NOT NULL,
	phone varchar(20) NULL,
	email varchar(100) NULL,
	joined_on timestamp NOT NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	CONSTRAINT users_pkey PRIMARY KEY (id),
	CONSTRAINT users_telegram_id_key UNIQUE (telegram_id)
);

CREATE TABLE public.available_days (
	id serial4 NOT NULL,
	appointment_date date NOT NULL,
	max_slots int4 DEFAULT 15 NULL,
	status varchar(10) DEFAULT 'active'::character varying NULL,
	CONSTRAINT available_days_appointment_date_key UNIQUE (appointment_date),
	CONSTRAINT available_days_pkey PRIMARY KEY (id)
);


CREATE TABLE public.appointments (
	id serial4 NOT NULL,
	user_id int4 NULL,
	appointment_date date NOT NULL,
	status public.status NULL,
	CONSTRAINT appointments_pkey PRIMARY KEY (id),
	created_at timestamp DEFAULT now() NOT NULL
);


-- public.appointments foreign keys
ALTER TABLE public.appointments ADD CONSTRAINT appointments_appointment_date_fkey FOREIGN KEY (appointment_date) REFERENCES public.available_days(appointment_date) ON DELETE CASCADE;
ALTER TABLE public.appointments ADD CONSTRAINT appointments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;



CREATE TABLE public.communion (
	id serial4 NOT NULL,
	user_id int4 NOT NULL,
	comm_date timestamp NULL,
	status public.status DEFAULT 'በመጠበቅ'::status NOT NULL,
	created_at timestamp DEFAULT now() NOT NULL,
	updated_at timestamp DEFAULT now() NOT NULL,
	CONSTRAINT communion_pkey PRIMARY KEY (id)
);


-- public.communion foreign keys

ALTER TABLE public.communion ADD CONSTRAINT communion_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


CREATE TABLE public.notifications (
	id serial4 NOT NULL,
	sent_to int8 NULL,
	sent_at timestamp DEFAULT now() NULL,
	message text NULL,
	CONSTRAINT notifications_pkey PRIMARY KEY (id)
);


-- public.notifications foreign keys

ALTER TABLE public.notifications ADD CONSTRAINT notifications_sent_to_fkey FOREIGN KEY (sent_to) REFERENCES public.users(telegram_id);


CREATE TABLE public.questions (
	id serial4 NOT NULL,
	telegram_id int8 NULL,
	question text NOT NULL,
	status public.status DEFAULT 'በመጠበቅ'::status NOT NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	CONSTRAINT questions_pkey PRIMARY KEY (id)
);


-- public.questions foreign keys

ALTER TABLE public.questions ADD CONSTRAINT questions_telegram_id_fkey FOREIGN KEY (telegram_id) REFERENCES public.users(telegram_id);


---seed data
INSERT INTO public.users
(id, telegram_id, "name", phone, email, joined_on, created_at, updated_at)
VALUES(nextval('users_id_seq'::regclass), admintelegramid, 'adminname', 'adminphone', 'adminemail', 'just randomdate', now(), now());