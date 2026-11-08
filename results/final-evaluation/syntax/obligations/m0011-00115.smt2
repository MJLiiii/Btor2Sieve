(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x3121 (and (distinct s_6 (_ bv7 4)) true)))
(not $x3121)))
(check-sat)
