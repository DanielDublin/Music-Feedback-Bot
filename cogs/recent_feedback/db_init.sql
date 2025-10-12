CREATE TABLE feedback_requests_mfs (
    request_id INT PRIMARY KEY AUTO_INCREMENT, -- will start from 1000 - what members use to respond to mfs
    message_id VARCHAR(255) UNIQUE NOT NULL, -- the message id when right click on message
    points_requested_to_use INT, -- how many points the mfs sender is requesting to use
    points_remaining INT, -- how many points the mfs sender has remaining (how many feedbacks they've gotten)
    status ENUM('open', 'partial', 'completed') DEFAULT 'open', -- will keep track of if feedback has been given or not
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- time when mfs was submitted
);

ALTER TABLE feedback_requests_mfs AUTO_INCREMENT = 1000;





DROP TABLE IF EXISTS feedback_requests_mfs;
