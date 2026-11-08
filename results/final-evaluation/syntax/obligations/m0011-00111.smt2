(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5269 (and (distinct s_6 (_ bv8 4)) true)))
(not $x5269)))
(check-sat)
