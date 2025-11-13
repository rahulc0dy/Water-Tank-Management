#include <Wire.h>
#include <NewPing.h>

#define TRIGGER_PIN 9
#define ECHO_PIN 10
#define LED_PIN 7
#define RELAY_PIN 5
#define BUZZER_PIN 6

#define MIN_DISTANCE 4
#define MAX_DISTANCE 11

NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE);

int prev_pump_state = 0;

const bool RELAY_ACTIVE_HIGH = true;

void setup() {
	Serial.begin(9600);
	pinMode(LED_PIN, OUTPUT);
	pinMode(RELAY_PIN, OUTPUT);
	pinMode(BUZZER_PIN, OUTPUT);

	digitalWrite(RELAY_PIN, RELAY_ACTIVE_HIGH ? LOW : HIGH);

}

void loop() {
	float level = getLevelPercent();

	Serial.print(level);
	Serial.print(",");
	Serial.print(prev_pump_state);
	// Serial.print(",");
	// if (level < 10) {
	// 	Serial.print("1");
	// 	prev_pump_state = 1;
	// }
	// else if(level >= 99.5) {
	// 	Serial.print("0");
	// 	prev_pump_state = 0;
	// }
	// else Serial.print(prev_pump_state);
	Serial.print("\n");

	if (Serial.available() > 0) {
		char command = Serial.read();
		controlPump(command);
	}
	
	delay(500);
}

void controlPump(char cmd) {
	if (cmd == '0') { 
		// OFF
		digitalWrite(RELAY_PIN, RELAY_ACTIVE_HIGH ? LOW : HIGH);
			
		prev_pump_state = 0;
	} else if (cmd == '1') { 
		// ON
		digitalWrite(RELAY_PIN, RELAY_ACTIVE_HIGH ? HIGH : LOW);
		// tone(BUZZER_PIN, 2000, 1000);
		digitalWrite(LED_PIN, HIGH);
		prev_pump_state = 1;
	}
}



float getLevelPercent() {
	unsigned int distance = sonar.ping_cm();
	if (distance == 0) return 0; 
	if (distance <= MIN_DISTANCE) return 100;
	if (distance >= MAX_DISTANCE) return 0;

	return ((float)(MAX_DISTANCE - distance) / (MAX_DISTANCE - MIN_DISTANCE)) * 100.0;
}
