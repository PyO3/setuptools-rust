import argparse

from ._lib import sum_as_string


def main():
    parser = argparse.ArgumentParser("sum 2 integers")
    parser.add_argument("x", type=int)
    parser.add_argument("y", type=int)
    args = parser.parse_args()
    print(f"{args.x} + {args.y} = {sum_as_string(args.x, args.y)}")


if __name__ == "__main__":
    main()
