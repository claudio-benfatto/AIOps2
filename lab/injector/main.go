// Package main is the entry point for the metasre-lab fault injector CLI.
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, os.Args[1:]); err != nil { //nolint:staticcheck // SA4023: false positive until M2 implements a command that can return nil
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(_ context.Context, args []string) error { //nolint:staticcheck // SA4023: no subcommand is implemented yet (M2 scope), so every path here errors
	if len(args) == 0 {
		return fmt.Errorf("usage: metasre-lab <inject|clear|reset> [args]")
	}

	switch cmd := args[0]; cmd {
	case "inject", "clear", "reset":
		return fmt.Errorf("command %q: not implemented yet", cmd)
	default:
		return fmt.Errorf("unknown command %q", cmd)
	}
}
