CREATE TABLE `asset_versions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`assetId` int NOT NULL,
	`version` int NOT NULL,
	`note` varchar(240),
	`payload` json NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `asset_versions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `assets` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandKitId` int NOT NULL,
	`type` enum('deck','website','email','pos','logo','visual','voice') NOT NULL,
	`variant` int NOT NULL,
	`schemaVersion` varchar(32) NOT NULL DEFAULT '1.0',
	`provider` varchar(80) NOT NULL DEFAULT 'claude',
	`status` enum('queued','ready','failed') NOT NULL DEFAULT 'queued',
	`payload` json NOT NULL,
	`previewUrl` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `assets_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `brand_kits` (
	`id` int AUTO_INCREMENT NOT NULL,
	`projectId` int NOT NULL,
	`strategyOptionId` int,
	`name` varchar(160) NOT NULL,
	`palette` json NOT NULL,
	`fonts` json NOT NULL,
	`voice` text NOT NULL,
	`tagline` text NOT NULL,
	`offer` text NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `brand_kits_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `niche_options` (
	`id` int AUTO_INCREMENT NOT NULL,
	`projectId` int NOT NULL,
	`optionNumber` int NOT NULL,
	`positioning` text NOT NULL,
	`targetCustomer` text NOT NULL,
	`coreOffer` text NOT NULL,
	`payload` json NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `niche_options_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `projects` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`name` varchar(160) NOT NULL,
	`niche` varchar(240) NOT NULL,
	`market` varchar(240) NOT NULL,
	`budget` varchar(80),
	`audience` varchar(320),
	`tone` varchar(120),
	`status` enum('draft','brand_locked','producing','ready') NOT NULL DEFAULT 'draft',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `projects_id` PRIMARY KEY(`id`)
);
