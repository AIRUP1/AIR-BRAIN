CREATE TABLE `pos_tickets` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandKitId` int NOT NULL,
	`ticketNumber` varchar(64) NOT NULL,
	`status` enum('quote','exported','void') NOT NULL DEFAULT 'quote',
	`currency` varchar(8) NOT NULL DEFAULT 'USD',
	`subtotalCents` int NOT NULL,
	`taxCents` int NOT NULL,
	`tipCents` int NOT NULL,
	`totalCents` int NOT NULL,
	`payload` json NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `pos_tickets_id` PRIMARY KEY(`id`),
	CONSTRAINT `pos_tickets_ticketNumber_unique` UNIQUE(`ticketNumber`)
);
