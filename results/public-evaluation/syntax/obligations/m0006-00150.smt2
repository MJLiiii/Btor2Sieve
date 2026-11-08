(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x128 (= s_4 (_ bv7 4))))
(not $x128)))
(check-sat)
