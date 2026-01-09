import argparse
# import configure
# import process

class App:
    '''
    Main application runstate.
    '''

    def configure(self) -> None:
        '''
        Runs the GUI configuration.
        '''
        print("Running Configuration!")

    def run(self) -> None:
        '''
        Runs the main process.
        '''
        print("Hello, world!")

if __name__ == "__main__":
    app = App()
    parser = argparse.ArgumentParser(
        description="Runs the script configuration."
        )
    parser.add_argument("--config",
                        action="store_true",
                        help="Launches the configration GUI."
                        )
    args = parser.parse_args()

    if args.config:
        app.configure()
    else:
        app.run()
