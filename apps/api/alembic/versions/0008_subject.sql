-- Subjects of the 2018 general education programme. Only DIA_LI is active: the others are a catalogue, not a promise.
CREATE TABLE subject (
	code TEXT NOT NULL,
	name_vi TEXT NOT NULL,
	active BOOLEAN DEFAULT false NOT NULL,
	PRIMARY KEY (code)
)
-- split
INSERT INTO subject (code, name_vi, active) VALUES
	('DIA_LI', 'Địa lí', true),
	('LICH_SU', 'Lịch sử', false),
	('TOAN', 'Toán', false),
	('NGU_VAN', 'Ngữ văn', false),
	('TIENG_ANH', 'Tiếng Anh', false),
	('VAT_LI', 'Vật lí', false),
	('HOA_HOC', 'Hóa học', false),
	('SINH_HOC', 'Sinh học', false),
	('TIN_HOC', 'Tin học', false),
	('CONG_NGHE', 'Công nghệ', false),
	('GDKT_PL', 'Giáo dục kinh tế và pháp luật', false)
