FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Lưu trạng thái delta ra volume để restart không gửi trùng
ENV STATE_FILE=/data/delta_state.json
VOLUME ["/data"]

CMD ["python", "src/main.py"]
