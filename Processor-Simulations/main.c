#include <stdio.h>
#include <stdint.h>

#define DEFINE_SAMPLE_INPUT
#include "fft.h"

// Output buffer for the FFT results
fft_cpx out_buf[FFT_SIZE] = {0};

// Function to slightly mutate input so the CPU stays busy with new data
void mutate_input(fft_cpx* data, int size, uint32_t iteration) {
    for (int i = 0; i < size; i++) {
        // Simple XOR/Add mutation to change bits and toggle gates
        data[i].r ^= (iteration & 0xFF);
        data[i].i += 1; 
    }
}

int main() {
    uint32_t iteration = 0;
    
    printf("[fft4k] Starting continuous power test...\n");

    // Infinite loop for continuous CPU load
    while (1) {
        // 1. Mutate the input (optional, but better for power testing)
        // Casting sample_input which is defined via "fft_twiddles.h"
        mutate_input((fft_cpx*)sample_input, FFT_SIZE, iteration);

        // 2. Run the Radix-4 FFT
        fft4((fft_cpx*)sample_input, out_buf);

        // 3. Periodic logging (don't log every time to avoid I/O bottlenecks)
        if (iteration % 1000 == 0) {
            printf("[fft4k] Iteration %u completed. CPU under load...\n", iteration);
        }

        iteration++;
    }

    return 0; // Never reached
}