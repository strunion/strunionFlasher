import argparse
import time
import serial
from crc import crc16, crc211

parser = argparse.ArgumentParser(description="Upload firmware to target")
parser.add_argument("file", help="firmware file")
parser.add_argument("--port", "-p", help="serial port", default="COM3")
parser.add_argument("--baud", "-b", help="baud rate", default=115200, type=int)
parser.add_argument("--start", "-s", help="start page", default=1, type=int)
parser.add_argument("--crypt", "-c", help="crypt", action="store_true")
parser.add_argument("--modbus", "-m", help="modbus", action="store_true")
parser.add_argument("--mAdr", "-ma", help="MB address", default=32, type=int)
parser.add_argument("--mBaud", "-mb", help="MB baud rate", default=9600, type=int)
parser.add_argument("--mReg", "-mr", help="MB register", default=65535, type=int)
parser.add_argument("--mVal", "-mv", help="MB value", default=0xDEAD, type=int)
args = parser.parse_args()

MAX_RETRIES = 10


def send_firmware(file, ser):
    with open(file, "rb") as f:
        data = f.read()

        data_list = [data[i : i + 1024] for i in range(0, len(data), 1024)]
        if len(data_list[-1]) < 1024:
            data_list[-1] += b"\xff" * (1024 - len(data_list[-1]))

        for _ in range(MAX_RETRIES):
            if args.modbus:
                ser.apply_settings(
                    {
                        "baudrate": args.mBaud,
                        "parity": serial.PARITY_NONE,
                        "stopbits": serial.STOPBITS_TWO,
                        "bytesize": serial.EIGHTBITS,
                    }
                )
                msg = (
                    args.mAdr.to_bytes(1, "big")
                    + b"\x06"
                    + args.mReg.to_bytes(2, "big")
                    + args.mVal.to_bytes(2, "big")
                )
                msg += crc16(msg).to_bytes(2, "little")
                ser.write(msg)
                time.sleep(8 * 11 / args.mBaud)

            ser.apply_settings({"baudrate": args.baud})

            ser.timeout = 0.01 + (4 * 11 / args.baud)
            while True:
                resp = ser.read(4)
                # print(resp)
                if resp == b"\xfe\xe1\xde\xad":
                    break

            ser.timeout = 0.1 + (1030 * 11 / args.baud)
            for i, page in enumerate(reversed(data_list)):
                print(f"Writing page {i + 1}/{len(data_list)}")
                ser.write(b"\xde\xad\xbe\xef")
                if args.crypt:
                    np = len(data_list) - i - 1 + 0x80 + args.start
                else:
                    np = len(data_list) - i - 1 + args.start
                ser.write(bytes([np]))
                ser.write(crc211(page).to_bytes(1, "little"))
                ser.write(page)
                resp = ser.read(1)
                if resp != b"\xAA":
                    print("Didn't get ACK, retrying...")
                    break
            else:
                print("Firmware upload successful!")
                return

            ser.reset_input_buffer()
            ser.reset_output_buffer()

        print("Max retries reached. Firmware upload unsuccessful.")


try:
    with serial.Serial(args.port, args.baud) as ser:
        send_firmware(args.file, ser)
except serial.SerialException as e:
    print(f"Serial port error: {e}")
except FileNotFoundError:
    print("File not found.")
except Exception as e:
    print(f"An error occurred: {e}")
