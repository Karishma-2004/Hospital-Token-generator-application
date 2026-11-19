import { Link } from "react-router-dom";
import {
  Hospital,
  CalendarCheck,
  ShieldCheck,
  Clock3,
  Users,
  Search,
  ArrowRight,
  CheckCircle2,
  Building2,
  UserPlus,
  LogIn,
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-slate-900">

      {/* =========================
          NAVBAR
      ========================== */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">

          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-3"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-600 text-white shadow-sm">
              <Hospital size={25} />
            </div>

            <div>
              <h1 className="text-xl font-black tracking-tight text-slate-900">
                Q<span className="text-green-600">enova</span>
              </h1>

              <p className="text-xs text-slate-500">
                Hospital Appointment Platform
              </p>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="hidden items-center gap-7 md:flex">

            <a
              href="#about"
              className="text-sm font-medium text-slate-600 transition hover:text-green-600"
            >
              About
            </a>

            <a
              href="#features"
              className="text-sm font-medium text-slate-600 transition hover:text-green-600"
            >
              Features
            </a>

            <a
              href="#how-it-works"
              className="text-sm font-medium text-slate-600 transition hover:text-green-600"
            >
              How It Works
            </a>

          </nav>

          {/* Auth Buttons */}
          <div className="flex items-center gap-2">

            <Link
              to="/login"
              className="hidden rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 sm:flex sm:items-center sm:gap-2"
            >
              <LogIn size={17} />
              Sign In
            </Link>

            <Link
              to="/register"
              className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700"
            >
              <UserPlus size={17} />
              Register
            </Link>

          </div>

        </div>
      </header>


      {/* =========================
          HERO SECTION
      ========================== */}
      <section className="overflow-hidden bg-gradient-to-br from-green-50 via-white to-slate-50">

        <div className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:py-24">

          {/* LEFT SIDE */}
          <div>

            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-4 py-2 text-sm font-semibold text-green-700">
              <CheckCircle2 size={17} />
              Simple & Secure Healthcare Booking
            </div>

            <h1 className="max-w-3xl text-4xl font-black leading-tight tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">

              Book Your Hospital
              <span className="block text-green-600">
                Appointment Easily
              </span>

            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Qenova helps patients discover hospitals, view available
              doctors and appointment slots, and book appointments online
              from one simple platform.
            </p>

            {/* Main Buttons */}
            <div className="mt-8 flex flex-wrap gap-4">

              <Link
                to="/register"
                className="flex items-center gap-2 rounded-xl bg-green-600 px-6 py-3.5 font-semibold text-white shadow-lg shadow-green-600/20 transition hover:bg-green-700"
              >
                Create Account
                <ArrowRight size={18} />
              </Link>

              <Link
                to="/login"
                className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3.5 font-semibold text-slate-700 transition hover:border-green-500 hover:text-green-700"
              >
                <LogIn size={18} />
                Sign In
              </Link>

            </div>

            {/* Small information */}
            <div className="mt-8 flex flex-wrap gap-6 text-sm text-slate-600">

              <div className="flex items-center gap-2">
                <CheckCircle2
                  size={18}
                  className="text-green-600"
                />
                Verified Hospitals
              </div>

              <div className="flex items-center gap-2">
                <CheckCircle2
                  size={18}
                  className="text-green-600"
                />
                Live Slot Availability
              </div>

              <div className="flex items-center gap-2">
                <CheckCircle2
                  size={18}
                  className="text-green-600"
                />
                Secure Booking
              </div>

            </div>

          </div>


          {/* RIGHT SIDE
              NO DOCTOR DETAILS
          */}
          <div className="relative">

            {/* Background decoration */}
            <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-green-100 blur-3xl" />

            <div className="relative mx-auto max-w-md">

              {/* Main Card */}
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl">

                {/* Header */}
                <div className="rounded-2xl bg-green-600 p-6 text-white">

                  <div className="flex items-center justify-between">

                    <div>
                      <p className="text-sm text-green-100">
                        Qenova
                      </p>

                      <h2 className="mt-1 text-2xl font-bold">
                        Find a Hospital
                      </h2>
                    </div>

                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/15">
                      <Hospital size={27} />
                    </div>

                  </div>

                  <div className="mt-5 flex items-center gap-3 rounded-xl bg-white/10 p-3">

                    <Search size={20} />

                    <span className="text-sm text-green-50">
                      Search hospitals and services
                    </span>

                  </div>

                </div>


                {/* Hospital cards */}
                <div className="mt-5 space-y-3">

                  <div className="flex items-center gap-4 rounded-2xl border border-slate-200 p-4">

                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-green-50 text-green-600">
                      <Building2 size={23} />
                    </div>

                    <div className="min-w-0 flex-1">

                      <p className="font-bold text-slate-800">
                        Approved Hospitals
                      </p>

                      <p className="mt-1 text-sm text-slate-500">
                        Browse hospitals available on Qenova
                      </p>

                    </div>

                    <ArrowRight
                      size={18}
                      className="text-slate-400"
                    />

                  </div>


                  <div className="flex items-center gap-4 rounded-2xl border border-slate-200 p-4">

                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                      <CalendarCheck size={23} />
                    </div>

                    <div className="min-w-0 flex-1">

                      <p className="font-bold text-slate-800">
                        Online Appointments
                      </p>

                      <p className="mt-1 text-sm text-slate-500">
                        Select an available appointment slot
                      </p>

                    </div>

                    <ArrowRight
                      size={18}
                      className="text-slate-400"
                    />

                  </div>


                  <div className="flex items-center gap-4 rounded-2xl border border-slate-200 p-4">

                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
                      <ShieldCheck size={23} />
                    </div>

                    <div className="min-w-0 flex-1">

                      <p className="font-bold text-slate-800">
                        Secure Booking
                      </p>

                      <p className="mt-1 text-sm text-slate-500">
                        Receive your appointment token
                      </p>

                    </div>

                    <ArrowRight
                      size={18}
                      className="text-slate-400"
                    />

                  </div>

                </div>

              </div>

              {/* Floating card */}
              <div className="absolute -bottom-6 -left-6 hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-xl sm:block">

                <div className="flex items-center gap-3">

                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-green-100 text-green-600">
                    <Clock3 size={22} />
                  </div>

                  <div>
                    <p className="text-xs text-slate-500">
                      Appointment
                    </p>

                    <p className="font-bold text-slate-800">
                      Slot Availability
                    </p>
                  </div>

                </div>

              </div>

            </div>

          </div>

        </div>

      </section>


      {/* =========================
          ABOUT SECTION
      ========================== */}
      <section
        id="about"
        className="bg-white px-6 py-20"
      >

        <div className="mx-auto max-w-7xl">

          <div className="max-w-3xl">

            <p className="text-sm font-bold uppercase tracking-wider text-green-600">
              About Qenova
            </p>

            <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl">
              A simpler way to manage hospital appointments
            </h2>

            <p className="mt-5 text-lg leading-8 text-slate-600">
              Qenova connects patients with approved hospitals through
              a centralized appointment booking platform. Patients can
              discover hospitals, view available services and appointment
              slots, and manage their bookings online.
            </p>

          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">

            <InfoCard
              icon={<Hospital size={24} />}
              title="Multiple Hospitals"
              text="Patients can browse approved hospitals from one platform."
            />

            <InfoCard
              icon={<CalendarCheck size={24} />}
              title="Easy Appointments"
              text="View available appointment slots and book without unnecessary waiting."
            />

            <InfoCard
              icon={<ShieldCheck size={24} />}
              title="Secure Platform"
              text="Account verification and controlled hospital access help keep the platform secure."
            />

          </div>

        </div>

      </section>


      {/* =========================
          FEATURES
      ========================== */}
      <section
        id="features"
        className="bg-slate-50 px-6 py-20"
      >

        <div className="mx-auto max-w-7xl">

          <div className="text-center">

            <p className="text-sm font-bold uppercase tracking-wider text-green-600">
              Features
            </p>

            <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl">
              Everything in one platform
            </h2>

            <p className="mx-auto mt-4 max-w-2xl text-slate-600">
              Qenova provides separate functionality for patients,
              hospitals, receptionists and doctors.
            </p>

          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">

            <FeatureCard
              icon={<Search size={24} />}
              title="Find Hospitals"
              text="Browse approved hospitals and choose the hospital you need."
            />

            <FeatureCard
              icon={<Users size={24} />}
              title="Hospital Services"
              text="View departments and doctors belonging to the selected hospital."
            />

            <FeatureCard
              icon={<Clock3 size={24} />}
              title="Available Slots"
              text="See available and booked appointment slots before booking."
            />

            <FeatureCard
              icon={<CalendarCheck size={24} />}
              title="Book Appointment"
              text="Select a slot and receive your appointment token."
            />

          </div>

        </div>

      </section>


      {/* =========================
          HOW IT WORKS
      ========================== */}
      <section
        id="how-it-works"
        className="bg-white px-6 py-20"
      >

        <div className="mx-auto max-w-7xl">

          <div className="text-center">

            <p className="text-sm font-bold uppercase tracking-wider text-green-600">
              How It Works
            </p>

            <h2 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl">
              Book your appointment in simple steps
            </h2>

          </div>

          <div className="mt-12 grid gap-8 md:grid-cols-4">

            <Step
              number="01"
              title="Create Account"
              text="Register on Qenova and verify your email."
            />

            <Step
              number="02"
              title="Choose Hospital"
              text="Browse the approved hospitals available on the platform."
            />

            <Step
              number="03"
              title="Select Slot"
              text="Choose a doctor and view available appointment slots."
            />

            <Step
              number="04"
              title="Book Appointment"
              text="Confirm the slot and receive your appointment token."
            />

          </div>

        </div>

      </section>


      {/* =========================
          CALL TO ACTION
      ========================== */}
      <section className="px-6 pb-20">

        <div className="mx-auto max-w-7xl">

          <div className="overflow-hidden rounded-3xl bg-slate-900 px-8 py-12 text-center text-white sm:px-12">

            <h2 className="text-3xl font-black sm:text-4xl">
              Ready to use Qenova?
            </h2>

            <p className="mx-auto mt-4 max-w-2xl text-slate-300">
              Create your account and start exploring hospitals and
              appointment availability.
            </p>

            <div className="mt-7 flex flex-wrap justify-center gap-3">

              <Link
                to="/register"
                className="flex items-center gap-2 rounded-xl bg-green-600 px-6 py-3 font-semibold text-white transition hover:bg-green-700"
              >
                <UserPlus size={18} />
                Register
              </Link>

              <Link
                to="/login"
                className="flex items-center gap-2 rounded-xl border border-slate-600 px-6 py-3 font-semibold text-white transition hover:bg-slate-800"
              >
                <LogIn size={18} />
                Sign In
              </Link>

            </div>

          </div>

        </div>

      </section>


      {/* =========================
          FOOTER
      ========================== */}
      <footer className="border-t border-slate-200 bg-white px-6 py-8">

        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-sm text-slate-500 md:flex-row">

          <div className="flex items-center gap-2">

            <Hospital
              size={19}
              className="text-green-600"
            />

            <span className="font-semibold text-slate-700">
              Qenova
            </span>

          </div>

          <p>
            Hospital Appointment Booking Platform
          </p>

          <div className="flex gap-5">

            <Link
              to="/login"
              className="hover:text-green-600"
            >
              Sign In
            </Link>

            <Link
              to="/register"
              className="hover:text-green-600"
            >
              Register
            </Link>

          </div>

        </div>

      </footer>

    </div>
  );
}


/* =================================
   REUSABLE COMPONENTS
================================= */

function InfoCard({ icon, title, text }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-50 text-green-600">
        {icon}
      </div>

      <h3 className="mt-5 text-lg font-bold text-slate-900">
        {title}
      </h3>

      <p className="mt-2 leading-7 text-slate-600">
        {text}
      </p>

    </div>
  );
}


function FeatureCard({ icon, title, text }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg">

      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-50 text-green-600">
        {icon}
      </div>

      <h3 className="mt-5 font-bold text-slate-900">
        {title}
      </h3>

      <p className="mt-2 text-sm leading-6 text-slate-600">
        {text}
      </p>

    </div>
  );
}


function Step({ number, title, text }) {
  return (
    <div className="text-center">

      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-600 font-bold text-white shadow-lg shadow-green-600/20">
        {number}
      </div>

      <h3 className="mt-5 font-bold text-slate-900">
        {title}
      </h3>

      <p className="mt-2 text-sm leading-6 text-slate-600">
        {text}
      </p>

    </div>
  );
}