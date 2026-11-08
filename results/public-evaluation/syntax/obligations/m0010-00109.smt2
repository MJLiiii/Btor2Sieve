(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x125 (= i_6 (_ bv128 8))))
(not $x125)))
(check-sat)
