SELECT
    op.row_number,
    op.object_class
FROM object_class_program_activity AS op
WHERE op.submission_id = {}
AND op.object_class NOT IN (SELECT object_class_code FROM object_class)
AND op.object_class NOT IN ('0000', '000', '00', '0')