(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x53 (= s_7 (_ bv128 8))))
(not $x53)))
(check-sat)
