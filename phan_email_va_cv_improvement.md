# PHẦN BỔ SUNG: CÁC TÍNH NĂNG MỞ RỘNG

---

## 3.2.5. Sinh email ứng tuyển tự động

### 3.2.5.1. Bối cảnh và mục tiêu

Sau khi người dùng hoàn thành AI CV Review và có thể đã xem qua các gợi ý cải thiện CV, bước tiếp theo tự nhiên trong quy trình ứng tuyển thực tế là soạn email gửi nhà tuyển dụng. Đây là một tác vụ mà nhiều ứng viên, đặc biệt sinh viên mới ra trường, thường gặp khó khăn do thiếu kinh nghiệm hoặc không biết nên nhấn mạnh điểm nào trong hồ sơ để tạo ấn tượng tốt.

Hệ thống bổ sung tính năng **Sinh email ứng tuyển tự động** nhằm hỗ trợ ứng viên trong bước này một cách cá nhân hóa, dựa trên toàn bộ thông tin đã phân tích từ CV và nghề nghiệp đã chọn. Khác với AI CV Review và AI CV Improvement được sinh tự động sau khi phân tích, tính năng này được kích hoạt **chủ động** khi người dùng bấm nút "Tạo email ứng tuyển", nhằm tiết kiệm chi phí LLM cho trường hợp người dùng chưa sẵn sàng ứng tuyển ngay.

### 3.2.5.2. Đầu vào và tái sử dụng dữ liệu

Email ứng tuyển sử dụng lại toàn bộ dữ liệu đã tính toán từ các bước trước đó trong cùng phiên làm việc, không thực hiện trích xuất hay tính toán mới:

- **Candidate Profile**: danh sách kỹ năng, kinh nghiệm, dự án, học vấn — đã trích xuất từ CV.
- **Occupation Profile**: kỹ năng cốt lõi, trách nhiệm công việc — đã tải từ cơ sở tri thức.
- **ScoreBreakdown**: Match Score, Semantic Similarity Score, Weighted Skill Score — đã tính.
- **SkillGap**: danh sách kỹ năng đã khớp và còn thiếu — đã phân tích.
- **AI CV Review** (nếu có): bối cảnh về đánh giá tổng quan và điểm mạnh — đã sinh.

Việc tái sử dụng dữ liệu này không chỉ tiết kiệm chi phí tính toán mà còn đảm bảo tính nhất quán: email luôn phản ánh đúng kết quả phân tích mà người dùng đã xem.

### 3.2.5.3. Thiết kế prompt và ràng buộc đầu ra

LLM được hướng dẫn sinh email theo một prompt được thiết kế cẩn thận với các ràng buộc sau:

**Ràng buộc về nội dung thực tế.** Email chỉ được xây dựng từ kỹ năng, kinh nghiệm và dự án thực sự có trong CV. Hệ thống tuyệt đối không cho phép LLM bịa thêm thành tích, số liệu, công nghệ hay kinh nghiệm không xuất hiện trong hồ sơ. Đây là nguyên tắc chống hallucination được áp dụng xuyên suốt, tương tự như ở AI CV Review.

**Ràng buộc về Matching Highlights.** Trước khi viết email, LLM phải tự xác định "matching highlights" — các điểm mạnh trong CV phù hợp nhất với vị trí — dựa trên kỹ năng đã khớp và kinh nghiệm liên quan. Các điểm này được ưu tiên nhấn mạnh trong email để tạo sự liên kết trực tiếp giữa năng lực của ứng viên và yêu cầu của vị trí.

**Ràng buộc về tính tự nhiên.** Email phải có giọng văn chuyên nghiệp nhưng tự nhiên, không rập khuôn theo mẫu cứng nhắc, với độ dài body từ 150 đến 250 từ. Email cần có đầy đủ các thành phần: lời chào, giới thiệu ngắn gọn, tên vị trí ứng tuyển, liên hệ kinh nghiệm với yêu cầu công việc, mong muốn phỏng vấn, lời cảm ơn và chữ ký.

**Ràng buộc về tên công ty.** Occupation Profile được tổng hợp từ rất nhiều tin tuyển dụng của nhiều công ty khác nhau và có thể vô tình chứa tên riêng của một công ty nào đó. LLM được yêu cầu tuyệt đối không coi đó là công ty ứng viên đang ứng tuyển và không nêu tên công ty cụ thể nào trong email, mà dùng cách xưng hô chung chung như "Kính gửi Bộ phận Tuyển dụng" hoặc "Kính gửi Quý công ty".

**Ràng buộc về tên ứng viên.** LLM được yêu cầu trích tên thật từ phần đầu CV gốc và sử dụng chính xác tên đó ở tiêu đề và chữ ký email, không được bịa ra tên ví dụ. Nếu CV không có tên rõ ràng, hệ thống sẽ bỏ qua tên trong chữ ký và sử dụng "Ứng viên" thay vì đoán bừa.

### 3.2.5.4. Định dạng đầu ra

Email được trả về dưới dạng JSON với ba trường: `subject` (tiêu đề email, ví dụ "Application for Lập trình viên Backend - Nguyễn Văn A"), `body` (toàn bộ nội dung email bao gồm lời chào và chữ ký, có xuống dòng giữa các đoạn), và `matching_highlights` (danh sách các điểm mạnh trong CV khớp nhất với vị trí, chỉ từ kỹ năng/kinh nghiệm thực có trong CV). Trường matching highlights được hiển thị riêng trên giao diện để người dùng thấy rõ lý do hệ thống nhấn mạnh các điểm đó.

### 3.2.5.5. Cơ chế phòng ngừa

**Ngưỡng độ đầy đủ hồ sơ.** Trước khi gọi LLM, hệ thống kiểm tra Candidate Profile có đủ thông tin để cá nhân hóa hay không. Nếu hồ sơ quá sơ sài (thiếu cả kỹ năng, kinh nghiệm và dự án), hệ thống trả về None thay vì sinh một email chung chung thiếu căn cứ. Điều này tránh tạo ấn tượng sai với nhà tuyển dụng và bảo vệ uy tín của ứng viên.

**Kiểm tra khả dụng LLM.** Nếu không có OPENAI_API_KEY hoặc dịch vụ LLM không phản hồi, hệ thống trả về None và hiển thị thông báo phù hợp trên giao diện, không làm gián đoạn các tính năng khác vẫn đang hoạt động.

---

## 3.2.6. Gợi ý cải thiện CV

### 3.2.6.1. Vai trò trong quy trình

AI CV Review đã phân tích và đánh giá CV dựa trên mức độ phù hợp với một vị trí cụ thể, chỉ ra điểm mạnh, điểm yếu và kỹ năng còn thiếu. Tuy nhiên, phần đánh giá chất lượng trình bày CV và các đề xuất cải thiện trong AI CV Review mang tính tổng quát, tập trung vào nội dung hơn là hình thức. Để đáp ứng nhu cầu thực tế của người dùng — không chỉ biết CV mình còn thiếu gì mà còn biết cách sửa như thế nào — hệ thống bổ sung **AI CV Improvement**, sinh một báo cáo riêng biệt tập trung vào việc cải thiện bố cục, chất lượng diễn đạt và viết lại các bullet yếu.

AI CV Improvement được sinh tự động sau AI CV Review (không cần người dùng bấm nút), sử dụng chung dữ liệu đầu vào với AI CV Review: Candidate Profile, Occupation Profile, ScoreBreakdown và SkillGap. Điểm khác biệt nằm ở prompt và đầu ra: thay vì đánh giá tổng thể mức độ phù hợp, AI CV Improvement tập trung hoàn toàn vào việc hướng dẫn người dùng cải thiện chính bản CV đang có.

### 3.2.6.2. Bốn phần đầu ra

AI CV Improvement trả về bốn phần được thiết kế cho bốn khía cạnh khác nhau của CV:

**Structure Review (Bố cục CV).** Phần này phân tích thứ tự và sự hiện diện của các mục chính trong CV: Tóm tắt/Objective, Kỹ năng, Kinh nghiệm, Học vấn, Dự án. Hệ thống nhận diện các tên gọi đồng nghĩa — ví dụ Summary, Objective, Profile, About Me, Introduction, Giới thiệu, Mục tiêu nghề nghiệp đều được coi là cùng một mục — để không báo thiếu khi mục đã có dưới tên gọi khác. Mỗi nhận xét phải chỉ rõ vị trí cụ thể trong CV, ví dụ: "Mục Học vấn đang đặt trên Kinh nghiệm, nên đảo xuống dưới" hoặc "Mục Kỹ năng nên đưa lên trước Kinh nghiệm để nhà tuyển dụng thấy ngay năng lực cốt lõi". Nếu bố cục đã hợp lý, phần này trả về mảng rỗng.

**Writing Review (Chất lượng diễn đạt).** Phần này phân tích cách ứng viên viết từng bullet kinh nghiệm và dự án. Các vấn đề được phát hiện bao gồm: bullet quá ngắn chỉ có 4-5 từ mà không nêu công nghệ hay kết quả, thiếu động từ hành động, thiếu số liệu định lượng, chưa nêu rõ vai trò hoặc đóng góp cụ thể. Mỗi vấn đề phải được giải thích lý do tại sao nó yếu, giúp người dùng hiểu nguyên tắc đằng sau lời khuyên thay vì chỉ nhận một danh sách sửa lỗi.

**Grammar Review (Ngữ pháp và chính tả).** Phần này liệt kê các lỗi chính tả, ngữ pháp, viết hoa, dấu câu và định dạng thực sự tìm thấy trong CV gốc. Hệ thống tự động phát hiện ngôn ngữ CV (tiếng Việt hoặc tiếng Anh) dựa trên mật độ ký tự có dấu tiếng Việt, và phân tích lỗi theo đúng ngôn ngữ đó. Nếu không phát hiện lỗi nào đáng kể, phần này trả về một câu thông báo theo ngôn ngữ tương ứng ("Không phát hiện lỗi chính tả/ngữ pháp đáng kể" cho tiếng Việt, "No major grammar issues detected" cho tiếng Anh).

**Rewrite Suggestions (Viết lại bullet yếu).** Đây là phần quan trọng nhất từ góc độ hành động. Hệ thống chọn ra các bullet kinh nghiệm hoặc dự án còn yếu — ngắn, chung chung, thiếu động từ hành động, thiếu số liệu, chưa nêu vai trò — và viết lại chúng rõ ràng và chuyên nghiệp hơn. Nguyên tắc cốt lõi: bản viết lại chỉ được diễn đạt lại hoặc làm rõ thông tin **đã có** trong CV, tuyệt đối không thêm số liệu, công nghệ hay kết quả không xuất hiện trong bullet gốc. Bản viết lại phải giữ đúng ngôn ngữ của bullet gốc — nếu bullet gốc viết bằng tiếng Anh thì bản viết lại cũng phải bằng tiếng Anh — vì ứng viên sẽ dán trực tiếp nội dung này vào CV của họ.

### 3.2.6.3. Xử lý đa ngôn ngữ

Hệ thống tự động phát hiện ngôn ngữ CV dựa trên mật độ ký tự có dấu tiếng Việt trên tổng số ký tự chữ cái, sử dụng ngưỡng 5% làm ranh giới. Việc phát hiện bằng mật độ (thay vì "có/không tuyệt đối") tránh nhầm một CV tiếng Anh có tên người Việt xuất hiện 1-2 lần thành CV tiếng Việt. Kết quả phát hiện ngôn ngữ ảnh hưởng đến hai phần đầu ra: Grammar Review (phân tích lỗi theo ngôn ngữ phù hợp) và Rewrite Suggestions (viết lại đúng ngôn ngữ bullet gốc).

### 3.2.6.4. Cơ chế kiểm soát chất lượng

Tương tự các tính năng khác dựa trên LLM, AI CV Improvement áp dụng cơ chế kiểm tra độ đầy đủ hồ sơ trước khi gọi LLM. Nếu CV quá sơ sài, hệ thống bỏ qua thay vì sinh nhận xét thiếu căn cứ. Đầu ra JSON cũng được chuẩn hóa sau khi nhận từ LLM để đảm bảo luôn có đủ bốn phần với kiểu dữ liệu đúng, phòng trường hợp LLM trả về thiếu hoặc sai định dạng.

---

## 3.2.7. Tổng hợp luồng xử lý hoàn chỉnh

Sau khi bổ sung hai tính năng mới, luồng xử lý hoàn chỉnh của hệ thống được mô tả như sau:

1. Người dùng tải CV lên hệ thống (PDF, DOCX hoặc Markdown).
2. Hệ thống trích xuất văn bản, kiểm tra tài liệu có phải CV hay không.
3. Xây dựng Candidate Profile (kỹ năng, kinh nghiệm, dự án, học vấn).
4. Tính Candidate Embedding một lần duy nhất.
5. Đối sánh với toàn bộ cơ sở tri thức nghề nghiệp (97 hồ sơ), tính Match Score.
6. Xếp hạng và hiển thị Top 3 nghề phù hợp nhất.
7. Người dùng chọn một nghề để xem đánh giá chi tiết.
8. Phân tích Skill Gap (Matched, Missing, Extra skills).
9. Sinh AI CV Review (gọi LLM một lần).
10. **Sinh AI CV Improvement tự động** (gọi LLM một lần tiếp theo, tập trung cải thiện CV).
11. Hiển thị kết quả: điểm số, AI CV Review, AI CV Improvement.
12. Người dùng có thể bấm "Tạo email ứng tuyển" để sinh email cá nhân hóa (**tùy chọn**, gọi LLM khi được yêu cầu).

Như vậy, tổng số lần gọi LLM trong một phiên làm việc hoàn chỉnh tối đa là ba: một cho AI CV Review, một cho AI CV Improvement, và một cho Email ứng tuyển (nếu người dùng chủ động yêu cầu). Cả hai tính năng mới đều tái sử dụng dữ liệu đã tính từ các bước trước đó, không phát sinh thêm trích xuất hay embedding, giữ cho chi phí tính toán ở mức tối ưu.
