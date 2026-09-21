CREATE TABLE `technician_availability` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandKitId` int NOT NULL,
	`technicianId` int NOT NULL,
	`weekday` int NOT NULL,
	`startMinutes` int NOT NULL,
	`endMinutes` int NOT NULL,
	`timeZone` varchar(80) NOT NULL DEFAULT 'America/Chicago',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `technician_availability_id` PRIMARY KEY(`id`)
);
