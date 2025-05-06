import argparse
from bintv.app import BintvApp


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", help="Target file")
    return parser.parse_args()


def main():
    args = parse_args()
    bintv_app = BintvApp(args.target)
    bintv_app.run()

if __name__ == '__main__':
    main()
