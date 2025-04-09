import csv


def main():
    # 打开文件准备写入
    with open('../data/user.csv', mode='w', newline='') as file:
        writer = csv.writer(file)

        # 写入表头
        writer.writerow(['username', 'password'])

        # 写入2000行数据
        for i in range(1, 2001):
            writer.writerow([f'user{i}', f'password{i}'])


if __name__ == '__main__':
    main()
