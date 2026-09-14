import fs from "fs";
import { FIXTURES_PATH } from "../global-setup";

export interface E2EFixtures {
  adminUsername: string;
  adminPassword: string;
  clientEmail: string;
  expiredTicketReference: string;
  expiredToken: string;
  mailpitUrl: string;
}

export function loadFixtures(): E2EFixtures {
  return JSON.parse(fs.readFileSync(FIXTURES_PATH, "utf-8"));
}
