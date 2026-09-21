CREATE TABLE `appointments` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandKitId` int NOT NULL,
	`ticketId` int NOT NULL,
	`technicianId` int NOT NULL,
	`startsAt` timestamp NOT NULL,
	`durationMinutes` int NOT NULL,
	`status` enum('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled',
	`notes` varchar(500),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `appointments_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `technicians` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandKitId` int NOT NULL,
	`name` varchar(160) NOT NULL,
	`role` varchar(120) NOT NULL DEFAULT 'Service technician',
	`initials` varchar(8) NOT NULL,
	`color` varchar(16) NOT NULL DEFAULT '#ddff51',
	`status` enum('active','inactive') NOT NULL DEFAULT 'active',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `technicians_id` PRIMARY KEY(`id`)
);
